from django.db import models
from django.core.validators import RegexValidator
from authenticationApp.models import User, ClinicDoctor
from doctorApp.models import VaccineSchedule


# Create your models here.

class Patient(models.Model):
    GENDER = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    doctor = models.ForeignKey(ClinicDoctor, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    child_name = models.CharField(max_length=255)
    date_of_birth = models.DateField()

    mobile_number = models.CharField(
        max_length=10,
        validators=[RegexValidator(regex=r'^\d{10}$', message="Mobile number must be 10 digits.")]
    )
    gender = models.CharField(max_length=155, choices=GENDER)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'child_name', 'date_of_birth']),
            models.Index(fields=['mobile_number', 'gender']),
            models.Index(fields=['is_active', 'created_at']),
        ]

        verbose_name_plural = 'Patient'

    def __str__(self):
        return self.child_name


class PatientVaccine(models.Model):
    COMPLETION_SOURCE = [
        ("Government Hospital", "Government Hospital"),
        ("Other Private Hospital", "Other Private Hospital"),
        ("Admin Doctor", "Admin Doctor"),
    ]

    STATUS_CHOICES = [
        ("Completed", "Completed"),
        ("Upcoming", "Upcoming"),
        ("Pending", "Pending"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="vaccines")

    custom_vaccine = models.CharField(max_length=150, null=True, blank=True)

    vaccine_schedule = models.ForeignKey(VaccineSchedule, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Upcoming")

    is_completed = models.BooleanField(default=False)
    completed_on = models.DateField(null=True, blank=True)

    completed_at = models.CharField(max_length=50, choices=COMPLETION_SOURCE, null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'patient']),
            models.Index(fields=['vaccine_schedule', 'status']),
            models.Index(fields=['is_completed', 'completed_on', 'custom_vaccine']),
            models.Index(fields=['completed_at', 'due_date', 'created_at']),
        ]

        verbose_name_plural = 'Patient Vaccine'
        unique_together = ("patient", "vaccine_schedule")

    def __str__(self):
        return f"{self.patient.child_name}"
