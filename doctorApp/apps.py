from django.apps import AppConfig


class DoctorappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "doctorApp"
    verbose_name = 'Doctors'

    def ready(self):
        # ✅ Import all Celery task modules here safely
        import doctorApp.firebase_utils
        import doctorApp.utils