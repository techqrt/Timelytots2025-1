import os
import datetime
import requests
import logging
from django.conf import settings
from django.utils import timezone
from patientApp.models import PatientVaccine
from doctorApp.models import ReminderLog
from celery import shared_task
from collections import defaultdict

# Setup logger
logger = logging.getLogger(__name__)

# WhatsApp API configs
WHATSAPP_API_URL = "https://graph.facebook.com/v20.0/<your_phone_number_id>/messages"
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")  # Set in .env


# --------------------------
# Generic WhatsApp Sender
# --------------------------
def send_whatsapp_template(to, template_name, components=None):
    """Send via Facebook Graph API (if you use it directly)."""
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    data = {
        "messaging_product": "whatsapp",
        "to": str(to),
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"},
        },
    }

    if components:
        data["template"]["components"] = components

    response = requests.post(WHATSAPP_API_URL, headers=headers, json=data)
    return _handle_response(response)


# --------------------------
# MSG91 WhatsApp Reminder
# --------------------------
def send_whatsapp_reminder(mobile_number, child_name, doctor_name, due_date, vaccine_name,age):
    """Send vaccine reminder via MSG91 WhatsApp API with vaccine name included."""
    url = "https://api.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/"
    headers = {
        "Content-Type": "application/json",
        "authkey": settings.MSG91_AUTH_KEY,
    }

    # Ensure proper international format (E.164 without +)
    if not str(mobile_number).startswith("91"):
        mobile_number = f"91{mobile_number}"

    payload = {
        "integrated_number": "918750138303",
        "content_type": "template",
        "payload": {
            "messaging_product": "whatsapp",
            "type": "template",
            "template": {
                "name": "vaccine_reminder1",
                "language": {"code": "en", "policy": "deterministic"},
                "namespace": "4e5add5b_52ed_4239_be4b_8b21e8a8f430",
                "to_and_components": [
                    {
                        "to": [mobile_number],
                        "components": {
                            "body_1": {"type": "text", "value": child_name},      # {{1}}
                            "body_2": {"type": "text", "value": str(due_date)},   # {{2}}
                            "body_3": {"type": "text", "value": vaccine_name},    # {{3}}
                            "body_4": {"type": "text", "value": age},             # {{4}}
                            "body_5": {"type": "text", "value": doctor_name},     # {{5}}
                            "body_6": {"type": "text", "value": f"+{mobile_number}"} # {{6}}
                        },
                    },
                ],
            },
        },
    }

    response = requests.post(url, headers=headers, json=payload)
    return _handle_response(response)



def send_registered_whatsapp(mobile_number, child_name, doctor_name):
    """Send welcome/intro message via MSG91 WhatsApp API."""
    url = "https://api.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/"
    headers = {
        "Content-Type": "application/json",
        "authkey": settings.MSG91_AUTH_KEY,
    }

    if not str(mobile_number).startswith("91"):
        mobile_number = f"91{mobile_number}"

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
                        "to": [mobile_number],
                        "components": {
                            "body_1": {"type": "text", "value": child_name},
                            "body_2": {"type": "text", "value": doctor_name},
                        },
                    }
                ],
            },
        },
    }

    response = requests.post(url, headers=headers, json=payload)
    return _handle_response(response)


# --------------------------
# Celery Tasks
# --------------------------
@shared_task
def send_vaccination_reminders():
    today = timezone.now().date()
    upcoming_vaccinations = PatientVaccine.objects.filter(
        due_date__gte=today, status="Upcoming"
    ).select_related("patient", "vaccine_schedule", "user")

    reminder_periods = [15, 7, 3, 0]
    print("Started sending vaccination reminders...")

    # Group vaccines by patient
    vaccines_by_patient = defaultdict(list)
    for vaccination in upcoming_vaccinations:
        days_left = (vaccination.due_date - today).days
        if days_left in reminder_periods:
            vaccines_by_patient[vaccination.patient.id].append(vaccination)

    for patient_id, patient_vaccines in vaccines_by_patient.items():
        patient = patient_vaccines[0].patient
        mobile_number = patient.mobile_number
        child_name = patient.child_name

        # Get doctor name from first vaccine (assuming same doctor for patient)
        doctor_name = patient_vaccines[0].user.full_name
        doctor_id = patient_vaccines[0].user.id

        # Combine all vaccine names
        vaccine_names = ", ".join(
            v.custom_vaccine if v.custom_vaccine else v.vaccine_schedule.vaccine
            for v in patient_vaccines
        )

        # Use the earliest due_date (or just today)
        due_date = min(v.due_date for v in patient_vaccines)

        # Get age from vaccine_schedule of the first vaccine
        age = patient_vaccines[0].vaccine_schedule.age

        # Send a single reminder
        response = send_whatsapp_reminder(
            mobile_number, child_name, doctor_name, due_date, vaccine_names, age
        )

        status = "success" if response.get("type") != "error" else "failed"

        # Save log to DB
        ReminderLog.objects.create(
            reminder_type="vaccination",
            recipient=mobile_number,
            child_name=child_name,
            doctor_name=doctor_name,
            doctor_id=str(doctor_id),
            vaccine_name=vaccine_names,
            due_date=due_date,
            status=status,
            response=response,
        )

        logger.info(f"Reminder logged for {mobile_number}, status={status}")

    return "Reminder job completed."


@shared_task
def test_celery():
    logger.info(f"[{datetime.datetime.now()}] Celery is working!")
    return "Success"


# --------------------------
# Helper for response handling
# --------------------------
def _handle_response(response):
    """Centralized response handler with logging."""
    try:
        resp_json = response.json()
    except Exception:
        resp_json = {"error": "Invalid JSON", "text": response.text}

    if response.status_code != 200:
        logger.error(f"❌ WhatsApp API failed: {response.status_code} - {resp_json}")
    else:
        logger.info(f"✅ WhatsApp API success: {resp_json}")

    return resp_json
