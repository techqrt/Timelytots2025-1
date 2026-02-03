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
from dashboardApp.utils import get_previous_month_range

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
    start_date, end_date = get_previous_month_range()
    if not created or instance.status != "success":
        return

    doctor_id = instance.doctor_id
    if not doctor_id:
        return

    try:
        doctor = User.objects.get(id=doctor_id)
    except User.DoesNotExist:
        return

    if doctor.billing_method not in [
        "Per Message",
        "Monthly Subscription",
        "Per Message + Monthly Subscription",
    ]:
        return

    # ✅ Count previous-month messages
    msg_count = ReminderLog.objects.filter(
        doctor_id=doctor_id,
        status="success",
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).count()

    billing, _ = BillingManagement.objects.get_or_create(
        user=doctor,
        billing_method=doctor.billing_method,
        payment_status="Pending",
        start_date=start_date,
        end_date=end_date,
        defaults={
            "total_message_sent": 0,
            "billing_subtotal": Decimal("0.00"),
            "gst_collected": Decimal("0.00"),
            "previous_dues": Decimal("0.00"),
            "total_bill_with_gst": Decimal("0.00"),
        },
    )

    billing.total_message_sent = msg_count
    billing.start_date = start_date
    billing.end_date = end_date

    per_msg_rate = Decimal(str(doctor.per_message_charges or 0))
    sub_fee = Decimal(str(doctor.monthly_subscription_fees or 0))

    if doctor.billing_method == "Per Message":
        subtotal = per_msg_rate * msg_count

    elif doctor.billing_method == "Monthly Subscription":
        subtotal = sub_fee

    else:
        subtotal = sub_fee + (per_msg_rate * msg_count)

    gst = subtotal * GST_RATE
    total = subtotal + gst

    billing.billing_subtotal = subtotal
    billing.gst_collected = gst
    billing.total_bill_with_gst = total
    billing.save()

