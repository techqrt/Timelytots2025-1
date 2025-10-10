from django.contrib import admin
from dashboardApp.models import Analytics, BillingManagement


@admin.register(Analytics)
class AnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'total_revenue',
        'pending_previous_month',
        'pending_this_month',
        'user_paid',
        'user_unpaid',
        'total_doctors',
        'active_patients',
        'total_message_sent',
    ]


@admin.register(BillingManagement)
class BillingManagementAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'billing_method',
        'total_message_sent',
        'billing_subtotal',
        'gst_collected',
        'previous_dues',
        'total_bill_with_gst',
        'payment_status',
    ]
