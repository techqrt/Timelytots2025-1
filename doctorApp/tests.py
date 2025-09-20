from django.test import TestCase
from django.utils import timezone
from patientApp.models import PatientVaccine, Patient
from .utils import send_vaccination_reminders
from django.contrib.auth import get_user_model

User = get_user_model()  # Use the custom user model

# Create your tests here.

class SendVaccinationRemindersTestCase(TestCase):
    def setUp(self):
        # Set up test data here
        self.user = User.objects.create(email='testuser@example.com', password='testpass')  # Use email instead of username
        self.patient = Patient.objects.create(
            user=self.user,  # Associate the user with the patient
            child_name='Test Child',
            date_of_birth='2020-01-01',
            mobile_number='8849558254',
            gender='Male'
        )
        self.vaccine = PatientVaccine.objects.create(
            patient=self.patient,
            user=self.user,  # Associate the user with the vaccine
            due_date=timezone.now().date() + timezone.timedelta(days=7),  # Due in 7 days
            status='Upcoming'
        )

    def test_send_vaccination_reminders(self):
        # Call the function to send reminders
        send_vaccination_reminders()
        # Check if the reminder was sent (you may need to mock the sending function)
        self.assertEqual(self.vaccine.status, 'Reminder Sent')  # Example assertion to check status
