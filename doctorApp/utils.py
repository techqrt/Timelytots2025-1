import requests
from django.conf import settings
import requests
import os
from django.utils import timezone
from patientApp.models import PatientVaccine  # Adjust the import based on your project structure
from celery import shared_task
import datetime

WHATSAPP_API_URL = "https://graph.facebook.com/v20.0/<your_phone_number_id>/messages"
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")  # set in .env


def send_whatsapp_template(to, template_name, components=None):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": str(to),
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"},
        }
    }

    if components:
        data["template"]["components"] = components

    response = requests.post(WHATSAPP_API_URL, headers=headers, json=data)
    return response.json()


def send_whatsapp_reminder(mobile_number, child_name, doctor_name, due_date):
    url = "https://api.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/"
    headers = {
        "Content-Type": "application/json",
        "authkey": settings.MSG91_AUTH_KEY,
    }

    payload = {
        "integrated_number": 918750138303,
        "content_type": "template",
        "payload": {
            "messaging_product": "whatsapp",
            "type": "template",
            "template": {
                "name": "vaccine_reminder1",
                "language": {
                    "code": "en",
                    "policy": "deterministic"
                },
                "namespace": "4e5add5b_52ed_4239_be4b_8b21e8a8f430",
                "to_and_components": [
                    {
                        "to": [
                            mobile_number
                        ],
                        "components": {
                            "body_1": {
                                "type": "text",
                                "value": f"Dear Parents, This is a friendly vaccine reminder for your child, {child_name}."
                            },
                            "body_2": {
                                "type": "text",
                                "value": f"The following vaccine(s) are due on: {due_date}"
                            },
                            "body_3": {
                                "type": "text",
                                "value": f"Please contact {doctor_name} to schedule an appointment or if you have any questions."
                            },
                            "body_4": {
                                "type": "text",
                                "value": "You can reach them at: {{6}}."
                            },
                            "body_5": {
                                "type": "text",
                                "value": "Thank you,"
                            },
                            "body_6": {
                                "type": "text",
                                "value": "Timely Tots Team"
                            }
                        }
                    }
                ]
            }
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    return response.json()


@shared_task
def send_vaccination_reminders():
    today = timezone.now().date()
    upcoming_vaccinations = PatientVaccine.objects.filter(due_date__gte=today, status='Upcoming')
    reminder_periods = [15, 7, 3, 0]  # Days before due date

    for vaccination in upcoming_vaccinations:
        due_date = vaccination.due_date
        days_left = (due_date - today).days

        if days_left in reminder_periods:
            mobile_number = vaccination.patient.mobile_number  # Assuming there's a related Patient model
            child_name = vaccination.patient.child_name  # Assuming there's a field for child's name
            doctor_name = vaccination.user.full_name  # Assuming there's a related Doctor model

            # Send the WhatsApp reminder
            response = send_whatsapp_reminder(mobile_number, child_name, doctor_name, due_date)
            print(f"Reminder sent to {mobile_number}: {response}")

def send_registered_whatsapp(mobile_number, child_name, doctor_name):
    url = "https://api.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/"
    headers = {
        "Content-Type": "application/json",
        "authkey": settings.MSG91_AUTH_KEY,
    }

    payload = {
        "integrated_number": "918750138303",
        "content_type": "template",
        "payload": {
            "messaging_product": "whatsapp",
            "type": "template",
            "template": {
                "name": "timelytots_intro",
                "language": {"code": "en", "policy": "deterministic"},
                "namespace": "4e5add5b_52ed_4239_be4b_8b21e8a8f430",
                "to_and_components": [
                    {
                        "to": [f"91{mobile_number}"],
                        "components": {
                            "body_1": {"type": "text", "value": child_name},
                            "body_2": {"type": "text", "value": doctor_name},
                        },
                    }
                ],
            },
        },
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()

@shared_task
def test_celery():
    print(f"[{datetime.datetime.now()}] Celery is working!")
    return "Success"

# Call the task periodically using Celery Beat
# In your settings.py, add the following:
# CELERY_BEAT_SCHEDULE = {
#     'send-reminders-every-day': {
#         'task': 'doctorApp.utils.send_vaccination_reminders',
#         'schedule': crontab(hour=8, minute=0),  # Adjust the time as needed
#     },
# }

