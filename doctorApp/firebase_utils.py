from celery import shared_task
from django.utils import timezone
from collections import defaultdict
from patientApp.models import PatientVaccine
from authenticationApp.models import User

import firebase_admin
from firebase_admin import credentials, messaging, firestore
from django.conf import settings
import logging
from timelytots import settings as setting
from doctorApp.models import FirebaseNotificationLog
from django.db import transaction

logger = logging.getLogger(__name__)


# Initialize Firebase once
if not firebase_admin._apps:
    cred = credentials.Certificate(setting.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)

# Firestore client (reuse same app)
db = firestore.client()

def save_notification_to_firestore(
    doctor_id,
    title,
    body,
    data=None,
    status="success",
    error=None,
):
    """
    Persist notification in Firestore at:
        user/{doctor_id}/notifications/{notification_id}

    This can be read directly from Flutter.
    """
    if not doctor_id:
        logger.warning("save_notification_to_firestore called without doctor_id.")
        return

    try:
        doc_ref = (
            db.collection("user")
            .document(str(doctor_id))
            .collection("notifications")
            .document()  # auto ID
        )

        payload = {
            "title": title,
            "body": body,
            "data": data or {},
            "status": status,           # 'success' or 'failed'
            "error": error,             # error message string or None
            "doctorId": str(doctor_id),
            "patientId": str(data.get("patient_id")) if data and data.get("patient_id") else None,
            "isRead": False,            # Flutter can toggle this when opened
            "createdAt": firestore.SERVER_TIMESTAMP,
        }

        # Remove keys with value None to keep Firestore clean
        payload = {k: v for k, v in payload.items() if v is not None}

        doc_ref.set(payload)
        logger.info(
            "📄 Notification stored in Firestore for doctor_id=%s, doc_id=%s",
            doctor_id,
            doc_ref.id,
        )
    except Exception as e:
        logger.exception(
            "Error saving notification to Firestore for doctor_id=%s: %s",
            doctor_id,
            e,
        )

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
        
        error_msg = "Missing FCM token"
        # Save in Firestore as failed notification
        save_notification_to_firestore(
            doctor_id=(data.get("doctor_id") if data else None),
            title=title,
            body=body,
            data=data,
            status="failed",
            error=error_msg,
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
        # Firestore: success notification
        save_notification_to_firestore(
            doctor_id=(data.get("doctor_id") if data else None),
            title=title,
            body=body,
            data=data,
            status="success",
            error=None,
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

        save_notification_to_firestore(
            doctor_id=(data.get("doctor_id") if data else None),
            title=title,
            body=body,
            data=data,
            status="failed",
            error=str(e),
        )
        return e

@shared_task
def send_missed_vaccine_notifications():
    """
    Daily task:
    Finds vaccines where due_date < today and status is not 'Completed',
    and notification_sent == False. Group by doctor and send a single
    notification per patient per doctor. Mark notification_sent=True on success.
    """
    today = timezone.now().date()

    missed_vaccines_qs = PatientVaccine.objects.filter(
        due_date__lt=today,
        is_completed=False,
        notification_sent=False,   # NEW: only those not yet notified
    ).exclude(status="Completed").select_related("patient", "user", "vaccine_schedule")

    if not missed_vaccines_qs.exists():
        logger.info("No missed vaccines found today (or all already notified).")
        return "No missed vaccines."

    # Group by doctor
    doctor_vaccines = defaultdict(list)
    for v in missed_vaccines_qs:
        # ensure user (doctor) exists on the object
        if not v.user_id:
            logger.warning("PatientVaccine id=%s missing user/doctor", v.id)
            continue
        doctor_vaccines[v.user.id].append(v)

    for doctor_id, vaccines in doctor_vaccines.items():
        try:
            doctor = User.objects.get(id=doctor_id)
        except User.DoesNotExist:
            logger.warning(f"⚠️ Doctor ID {doctor_id} not found.")
            continue

        if not getattr(doctor, "fcm_token", None):
            logger.warning(f"⚠️ Doctor {getattr(doctor, 'full_name', doctor_id)} missing FCM token.")
            continue

        # Group vaccines by patient for this doctor
        patient_vaccines = defaultdict(list)
        for v in vaccines:
            if not v.patient_id:
                logger.warning("PatientVaccine id=%s missing patient", v.id)
                continue
            patient_vaccines[v.patient.id].append(v)

        for patient_id, pv_list in patient_vaccines.items():
            # Build vaccine_names and patient info from pv_list (unlocked objects)
            patient = pv_list[0].patient
            patient_name = getattr(patient, "child_name", "the patient")
            mobile_number = getattr(patient, "mobile_number", "N/A")
            vaccine_names = ", ".join(
                v.custom_vaccine if v.custom_vaccine else getattr(v.vaccine_schedule, "vaccine", "")
                for v in pv_list
            )

            title = "Missed Vaccine Alert"
            body = (
                f"Due date missed for {patient_name} for {vaccine_names}. "
                f"You can reach {patient_name} at {mobile_number}."
            )

            # Concurrency protection: re-lock involved PatientVaccine rows and confirm they're still not notified
            pv_ids = [v.id for v in pv_list]
            try:
                with transaction.atomic():
                    claimed = (
                    PatientVaccine.objects
                    .filter(id__in=pv_ids, notification_sent=False)
                    .update(
                        notification_sent=True,
                        notification_sent_at=timezone.now(),
                        )
                    )

                    if claimed != len(pv_ids):
                        logger.info(
                            "Partial/no claim for pv_ids=%s (claimed=%s). Skipping notification.",
                            pv_ids,
                            claimed,
                        )
                        continue

                    # Send notification
                    send_result = send_firebase_notification(
                        doctor.fcm_token,
                        title,
                        body,
                        data={
                            "doctor_id": str(doctor.id),
                            "patient_id": str(patient.id),
                            "vaccine_names": vaccine_names,
                        },
                    )

                    # Determine success: your send_firebase_notification returns True on success,
                    # and an Exception object or False on failure based on your current code.
                    if send_result is not True:
                        PatientVaccine.objects.filter(id__in=pv_ids).update(
                            notification_sent=False,
                            notification_sent_at=None,
                        )

                        logger.error(
                            "Notification failed for doctor=%s patient=%s. Rolled back claim.",
                            doctor_id,
                            patient_id,
                        )
                    else:
                        # send failed; do not mark as notified so it can retry later
                        logger.error(
                            "Failed to send notification for doctor=%s patient=%s. send_result=%s",
                            doctor_id, patient_id, str(send_result)
                        )
                        # optionally, you could save a retry counter or other logic here

            except Exception as e:
                logger.exception(
                    "Exception while sending/marking notifications for doctor=%s patient=%s: %s",
                    doctor_id, patient_id, e
                )
                # Without marking notification_sent, it will be retried later

    return "Missed vaccine notifications processed."