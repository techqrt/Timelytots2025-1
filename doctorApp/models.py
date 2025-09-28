from django.db import models
from django.conf import settings

from authenticationApp.models import User


# Create your models here.

class VaccineSchedule(models.Model):
    class AgeChoices(models.TextChoices):
        BIRTH = "Birth", "Birth"
        SIX_WEEKS = "6 Weeks", "6 Weeks"
        TEN_WEEKS = "10 Weeks", "10 Weeks"
        FOURTEEN_WEEKS = "14 Weeks", "14 Weeks"
        SIX_MONTHS = "6 Months", "6 Months"
        SEVEN_MONTHS = "7 Months", "7 Months"
        NINE_MONTHS = "9 Months", "9 Months"
        TWELVE_MONTHS = "12 Months", "12 Months"
        FIFTEEN_MONTHS = "15 Months", "15 Months"
        SIXTEEN_EIGHTEEN_MONTHS = "16–18 Months", "16–18 Months"
        EIGHTEEN_MONTHS = "18 Months", "18 Months"
        TWO_YEARS = "2 Years", "2 Years"
        THREE_YEARS = "3 Years", "3 Years"
        FOUR_YEARS = "4 Years", "4 Years"
        FOUR_SIX_YEARS = "4–6 Years", "4–6 Years"
        FIVE_YEARS = "5 Years", "5 Years"
        SIX_YEARS = "6 Years", "6 Years"
        SEVEN_YEARS = "7 Years", "7 Years"
        EIGHT_YEARS = "8 Years", "8 Years"
        TEN_YEARS = "10 Years", "10 Years"
        SIXTEEN_EIGHTEEN_YEARS = "16–18 Years", "16–18 Years"

    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    ACCOUNT_TYPE_CHOICES = [
        ("doctor", "Individual Doctor"),
        ("clinic", "Clinic / Hospital"),
    ]

    clinic_doctor = models.ForeignKey(
        "authenticationApp.ClinicDoctor",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="vaccine_schedules"
    )
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        null=True, blank=True
    )
    patient = models.ForeignKey(
        "patientApp.Patient",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="custom_vaccine_schedules"
    )
    age = models.DateField(blank=True, null=True)

    due_date = models.DateField(blank=True, null=True)

    vaccine = models.CharField(max_length=150)
    
    def __str__(self):
        return f"{self.age} → {self.vaccine}"
