from django.test import TestCase
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta, date
from authenticationApp.models import User
from patientApp.models import Patient, VaccineSchedule, PatientVaccine
from doctorApp.firebase_utils import send_missed_vaccine_notifications


class MissedVaccineNotificationTest(TestCase):
    """Tests for send_missed_vaccine_notifications Celery task"""

    def setUp(self):
        # Create a dummy doctor
        self.doctor = User.objects.create(
            full_name="Dr. Test Doctor",
            email="doctor@test.com",
            account_type="doctor",
            billing_method="Per Message",
            per_message_charges=2,
            monthly_subscription_fees=100,
            fcm_token="dDAd6XyCTyO4nCHxCXjMg1:APA91bFjRTx30KfuaWcXbi0voEtwwb2jVzcXttr_QsgMR64cx7LKzxqI2xZVOXyM3UCus4145-1n-TErc-p9qZmF6Uzhn5AvTaKgi_GbSNMzWMuNpb83WWU",
            is_active=True,
        )

        # Create a dummy patient
        self.patient = Patient.objects.create(
            user=self.doctor,
            child_name="John Doe",
            mobile_number="8708559274",
            date_of_birth=date(2020, 1, 1)
        )

        # Create a dummy vaccine schedule
        self.schedule = VaccineSchedule.objects.create(
            vaccine="Polio Vaccine",
            age="6 weeks"
        )

        # Create a PatientVaccine due yesterday (missed)
        yesterday = timezone.now().date() - timedelta(days=1)
        self.vaccine = PatientVaccine.objects.create(
            patient=self.patient,
            user=self.doctor,
            vaccine_schedule=self.schedule,
            due_date=yesterday,
            status="Upcoming"
        )

    @patch("doctorApp.firebase_utils.send_firebase_notification")
    def test_send_missed_vaccine_notifications(self, mock_send_firebase):
        """Ensure missed vaccine notification is sent to doctor"""

        # Mock Firebase to always return True
        mock_send_firebase.return_value = True

        # Run the Celery task directly
        result = send_missed_vaccine_notifications()

        # Assertions
        self.assertEqual(result, "Missed vaccine notifications sent.")
        self.assertTrue(mock_send_firebase.called, "Firebase was not called")

        # Extract positional & keyword arguments
        pos_args, kw_args = mock_send_firebase.call_args
        fcm_token, title, body = pos_args
        data = kw_args.get("data", {})

        # Verify message content
        self.assertEqual(title, "Missed Vaccine Alert")
        self.assertIn("John Doe", body)
        self.assertIn("Polio Vaccine", body)
        self.assertIn("8708559274", body)

        # Verify data payload keys
        self.assertIn("doctor_id", data)
        self.assertIn("patient_id", data)
        self.assertIn("vaccine_names", data)

        print("✅ Test passed — Firebase called with correct data and body.")
