from django.contrib import admin
from django.urls import path
from django.http import HttpResponseRedirect
from django.contrib import messages

from .models import VaccineSchedule, ReminderLog, FirebaseNotificationLog
from . import utils 

# Register your models here.

@admin.register(FirebaseNotificationLog)
class FirebaseNotificationLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "doctor_id",
        "patient_id",
        "title",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("doctor_id", "patient_id", "title", "body")
    readonly_fields = (
        "doctor_id",
        "patient_id",
        "title",
        "body",
        "data",
        "status",
        "response",
        "created_at",
    )
    ordering = ("-created_at",)
    list_per_page = 50

    fieldsets = (
        ("Doctor & Patient Info", {
            "fields": ("doctor_id", "patient_id")
        }),
        ("Notification Details", {
            "fields": ("title", "body", "data", "status", "response")
        }),
        ("Timestamps", {
            "fields": ("created_at",)
        }),
    )


@admin.register(ReminderLog)
class ReminderLogAdmin(admin.ModelAdmin):
    list_display = ("doctor_id","reminder_type", "recipient", "child_name", "doctor_name", "vaccine_name", "due_date", "status", "created_at")
    list_filter = ("reminder_type", "status", "created_at")
    search_fields = ("recipient", "child_name", "doctor_name", "vaccine_name")

@admin.register(VaccineSchedule)
class VaccineScheduleAdmin(admin.ModelAdmin):
    list_display = ("id", "vaccine", "age", "due_date", "user")

    def get_urls(self):
        """Extend admin URLs to include custom 'send_reminders' endpoint."""
        urls = super().get_urls()
        custom_urls = [
            path(
                "send-reminders/",
                self.admin_site.admin_view(self.send_reminders),
                name="send_vaccine_reminders",
            ),
        ]
        return custom_urls + urls

    def send_reminders(self, request):
        """Admin view that triggers reminder sending."""
        try:
            # If using Celery (async)
            utils.send_vaccination_reminders.delay()
            print("Vaccination reminders task has been queued.")

            # If you want to run sync (not recommended in prod):
            # utils.send_vaccination_reminders()

            messages.success(request, "✅ Vaccination reminders have been triggered successfully.")
        except Exception as e:
            messages.error(request, f"❌ Error while sending reminders: {e}")

        # Redirect back to changelist
        return HttpResponseRedirect("../")

    def changelist_view(self, request, extra_context=None):
        """Inject extra context for custom button in template."""
        extra_context = extra_context or {}
        extra_context["custom_button_url"] = "send-reminders/"
        return super().changelist_view(request, extra_context=extra_context)
