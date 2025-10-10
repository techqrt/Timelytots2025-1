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


@receiver(post_save, sender=apps.get_model('doctorApp', 'ReminderLog'))
def update_billing_from_reminder(sender, instance, created, **kwargs):
    print("🔔 ReminderLog saved:", instance.id, instance.status, created)  # Debug check
    if not created or instance.status != "success":
        print("❌ Not created or not success, skipping")
        return

    doctor_id = instance.doctor_id
    if not doctor_id:
        print("❌ No doctor_id found, skipping")
        return

    try:
        doctor = User.objects.get(id=doctor_id)
        print("✅ Found doctor:", doctor.full_name)
    except User.DoesNotExist:
        print("❌ Doctor not found:", doctor_id)
        return

    if doctor.billing_method not in ["Per Message", "Per Message + Monthly Subscription"]:
        print("🚫 Not eligible billing method:", doctor.billing_method)
        return

    if not doctor.per_message_charges:
        print("🚫 Missing per_message_charges")
        return

    billing, created = BillingManagement.objects.get_or_create(
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

    billing.total_message_sent += 1
    billing.billing_subtotal += Decimal(doctor.per_message_charges)
    billing.gst_collected = billing.billing_subtotal * GST_RATE
    billing.total_bill_with_gst = billing.billing_subtotal + billing.gst_collected
    billing.save()
    print("✅ Billing updated for", doctor.full_name, "→", billing.total_message_sent)