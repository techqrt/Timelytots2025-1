from django.apps import apps
from django.db.models.signals import post_save, post_delete
from django.db.models import Sum
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal

from doctorApp.models import ReminderLog
from dashboardApp.models import BillingManagement
from authenticationApp.models import User, ClinicDoctor
from dashboardApp.models import Analytics

GST_RATE = Decimal('0.18')

# --- Helper Function ---
def update_analytics_counts():
    total_doctors = ClinicDoctor.objects.count()
    active_patients = User.objects.filter(is_active=True, account_type='doctor').count()
    total_message_sent = BillingManagement.objects.aggregate(total=Sum('total_message_sent'))['total'] or 0

    analytics, created = Analytics.objects.get_or_create(id=1)
    analytics.total_doctors = total_doctors
    analytics.active_patients = active_patients
    analytics.total_message_sent = total_message_sent
    analytics.save()


# --- Signal: Update when doctors change ---
@receiver([post_save, post_delete], sender=ClinicDoctor)
def update_total_doctors(sender, **kwargs):
    update_analytics_counts()


# --- Signal: Update when user (doctor/patient) changes ---
@receiver([post_save, post_delete], sender=User)
def update_active_patients(sender, **kwargs):
    update_analytics_counts()


# --- Signal: Update revenue whenever billing changes ---
@receiver([post_save, post_delete], sender=BillingManagement)
def update_total_revenue(sender, **kwargs):
    total_revenue = BillingManagement.objects.aggregate(total=Sum('total_bill_with_gst'))['total'] or 0
    pending_previous_month = BillingManagement.objects.filter(payment_status='Pending').aggregate(total=Sum('total_bill_with_gst'))['total'] or 0
    user_paid = BillingManagement.objects.filter(payment_status='Paid').aggregate(total=Sum('total_bill_with_gst'))['total'] or 0
    user_unpaid = BillingManagement.objects.filter(payment_status__in=['Pending', 'In Process']).aggregate(total=Sum('total_bill_with_gst'))['total'] or 0

    analytics, created = Analytics.objects.get_or_create(id=1)
    analytics.total_revenue = total_revenue
    analytics.pending_previous_month = pending_previous_month
    analytics.user_paid = user_paid
    analytics.user_unpaid = user_unpaid
    analytics.save()


@receiver(post_save, sender=apps.get_model("doctorApp", "ReminderLog"))
def update_billing_from_reminder(sender, instance, created, **kwargs):
    """
    Automatically updates billing when a successful reminder is sent.
    Handles: Individual Doctors + Clinic Doctors.
    For 'Monthly Subscription' only increments message count (no cost added).
    """
    if not created or instance.status != "success":
        return

    doctor_id = instance.doctor_id
    if not doctor_id:
        return

    try:
        doctor = User.objects.get(id=doctor_id)
    except User.DoesNotExist:
        print(f"⚠️ No User found with ID={doctor_id}, skipping billing.")
        return

    if doctor.billing_method not in [
        "Per Message",
        "Monthly Subscription",
        "Per Message + Monthly Subscription",
    ]:
        return

    # Ensure there’s a BillingManagement record (create if missing)
    billing, _ = BillingManagement.objects.get_or_create(
        user=doctor,
        billing_method=doctor.billing_method,
        payment_status="Pending",
        defaults={
            "total_message_sent": 0,
            "billing_subtotal": Decimal("0.00"),
            "gst_collected": Decimal("0.00"),
            "previous_dues": Decimal("0.00"),
            "total_bill_with_gst": Decimal("0.00"),
        },
    )

    # ✅ Always increment message count (for reporting/analytics)
    billing.total_message_sent += 1

    # 💰 Only charge for per-message or hybrid billing
    if doctor.billing_method in ["Per Message", "Per Message + Monthly Subscription"]:
        if doctor.per_message_charges:
            billing.billing_subtotal += Decimal(doctor.per_message_charges)
        else:
            print(f"⚠️ No per_message_charges for {doctor.full_name}")

        # Include subscription in hybrid model
        subscription_fee = (
            Decimal(doctor.monthly_subscription_fees)
            if doctor.billing_method == "Per Message + Monthly Subscription"
            else Decimal("0.00")
        )

        combined_total = billing.billing_subtotal + subscription_fee
        billing.gst_collected = combined_total * GST_RATE
        billing.total_bill_with_gst = combined_total + billing.gst_collected

    # 🧾 For Monthly Subscription only → no charges, no GST
    elif doctor.billing_method == "Monthly Subscription":
        billing.gst_collected = Decimal("0.00")
        billing.total_bill_with_gst = Decimal("0.00")

    billing.save()
    print(
        f"✅ Billing updated for {doctor.full_name} ({doctor.billing_method}) "
        f"→ Total messages: {billing.total_message_sent}, "
        f"Total Bill: {billing.total_bill_with_gst}"
    )
