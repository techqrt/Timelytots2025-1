from celery import shared_task
from django.utils import timezone
from collections import defaultdict
from patientApp.models import PatientVaccine
from authenticationApp.models import User

import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
import logging
from timelytots import settings as setting
from doctorApp.models import FirebaseNotificationLog


logger = logging.getLogger(__name__)

# Initialize Firebase once
if not firebase_admin._apps:
    cred = credentials.Certificate(setting.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)


def send_firebase_notification(fcm_token, title, body, data=None):
    """
    Send a push notification using Firebase Cloud Messaging
    and log the notification details.
    """
    if not fcm_token:
        FirebaseNotificationLog.objects.create(
            title=title,
            body=body,
            data=data,
            status="failed",
            response={"error": "Missing FCM token"},
            doctor_id=(data.get("doctor_id") if data else None),
            patient_id=(data.get("patient_id") if data else None),
        )
        return False

    from firebase_admin import messaging

    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            token=fcm_token,
        )
        response = messaging.send(message)

        FirebaseNotificationLog.objects.create(
            title=title,
            body=body,
            data=data,
            status="success",
            response={"firebase_response": response},
            doctor_id=(data.get("doctor_id") if data else None),
            patient_id=(data.get("patient_id") if data else None),
        )

        return True

    except Exception as e:
        FirebaseNotificationLog.objects.create(
            title=title,
            body=body,
            data=data,
            status="failed",
            response={"error": str(e)},
            doctor_id=(data.get("doctor_id") if data else None),
            patient_id=(data.get("patient_id") if data else None),
        )
        return e

@shared_task
def send_missed_vaccine_notifications():
    """
    Daily task:
    Finds vaccines where due_date < today and status is not 'Completed',
    groups by doctor, and sends a Firebase notification.
    """
    today = timezone.now().date()
    missed_vaccines = (
        PatientVaccine.objects.filter(due_date__lt=today)
        .exclude(status__in=["Completed", "Missed"], is_completed=False)
        .select_related("patient", "user", "vaccine_schedule")
    )

    if not missed_vaccines.exists():
        logger.info("No missed vaccines found today.")
        return "No missed vaccines."

    # Group by doctor
    doctor_vaccines = defaultdict(list)
    for v in missed_vaccines:
        doctor_vaccines[v.user.id].append(v)

    for doctor_id, vaccines in doctor_vaccines.items():
        try:
            doctor = User.objects.get(id=doctor_id)
        except User.DoesNotExist:
            logger.warning(f"⚠️ Doctor ID {doctor_id} not found.")
            continue

        if not doctor.fcm_token:
            logger.warning(f"⚠️ Doctor {doctor.full_name} missing FCM token.")
            continue

        # Group vaccines by patient for this doctor
        patient_vaccines = defaultdict(list)
        for v in vaccines:
            patient_vaccines[v.patient.id].append(v)

        # Send one notification per patient
        for patient_id, pv_list in patient_vaccines.items():
            patient = pv_list[0].patient
            patient_name = patient.child_name
            mobile_number = patient.mobile_number
            vaccine_names = ", ".join(
                v.custom_vaccine if v.custom_vaccine else v.vaccine_schedule.vaccine
                for v in pv_list
            )

            title = "Missed Vaccine Alert"
            body = (
                f"Due date missed for {patient_name} for {vaccine_names}. "
                f"You can reach {patient_name} at {mobile_number}."
            )

            # Send Firebase Notification
            send_firebase_notification(
                doctor.fcm_token,
                title,
                body,
                data={
                    "doctor_id": str(doctor.id),
                    "patient_id": str(patient.id),
                    "vaccine_names": vaccine_names,
                },
            )

            logger.info(f"📨 Notification sent to {doctor.full_name} for {patient_name}")

    return "Missed vaccine notifications sent."