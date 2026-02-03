from django.db import models
from django.core.validators import RegexValidator, EmailValidator
from authenticationApp.models import User, ClinicDoctor
from datetime import date


# Create your models here.


class Analytics(models.Model):
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    pending_previous_month = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    pending_this_month = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    user_paid = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    user_unpaid = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    total_doctors = models.PositiveIntegerField(blank=True, null=True)

    active_patients = models.PositiveIntegerField(blank=True, null=True)
    total_message_sent = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['total_revenue', 'pending_previous_month']),
            models.Index(fields=['pending_this_month', 'user_paid']),
            models.Index(fields=['user_unpaid', 'total_doctors']),
            models.Index(fields=['active_patients', 'total_message_sent']),
        ]

        verbose_name_plural = 'Analytics'

    def save(self, *args, **kwargs):
        self.total_doctors = ClinicDoctor.objects.count()
        super().save(*args, **kwargs)

    def __str__(self):
        return 'Analytics data'



class BillingManagement(models.Model):
    PAYMENT_STATUS = [
        ('In Process', 'In Process'),
        ('Pending', 'Pending'),
        ('Failed', 'Failed'),
        ('Paid', 'Paid'),
    ]

    BILLING_METHOD = [
        ('Per Message', 'Per Message'),
        ('Monthly Subscription', 'Monthly Subscription'),
        ('Per Message + Monthly Subscription', 'Per Message + Monthly Subscription'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="billing_user")
    billing_method = models.CharField(choices=BILLING_METHOD, max_length=155, blank=True, null=True)

    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    total_message_sent = models.PositiveIntegerField()
    billing_subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    gst_collected = models.DecimalField(max_digits=10, decimal_places=2)

    previous_dues = models.DecimalField(max_digits=10, decimal_places=2)
    total_bill_with_gst = models.DecimalField(max_digits=10, decimal_places=2)

    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS, blank=True, null=True, default='Pending')

    class Meta:
        indexes = [
            models.Index(fields=['user', 'billing_method']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['total_message_sent', 'billing_subtotal', 'gst_collected']),
            models.Index(fields=['previous_dues', 'total_bill_with_gst']),
            models.Index(fields=['payment_status']),
        ]
        verbose_name_plural = 'Billing Management'

    def __str__(self):
        return str(self.user)


