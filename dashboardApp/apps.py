from django.apps import AppConfig


class DashboardappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dashboardApp"
    verbose_name = "Dashboard"

    def ready(self):
        import dashboardApp.signals