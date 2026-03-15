from django.core.management.base import BaseCommand

from doctorApp.utils import send_vaccination_reminders


class Command(BaseCommand):
    help = "Send daily vaccine reminders via WhatsApp"

    def handle(self, *args, **kwargs):
        send_vaccination_reminders()
        self.stdout.write(self.style.SUCCESS("Vaccine reminders sent successfully"))

