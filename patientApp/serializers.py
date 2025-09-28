from rest_framework import serializers

from authenticationApp.models import User, ClinicDoctor
from doctorApp.models import VaccineSchedule
from patientApp.models import Patient, PatientVaccine
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


class PatientVaccineSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.child_name", read_only=True)
    vaccine_name = serializers.SerializerMethodField()
    vaccine_age = serializers.CharField(source="vaccine_schedule.age", read_only=True)
    created_at = serializers.DateTimeField(format="%d-%b-%Y at %I:%M %p", read_only=True)
    custom_age = serializers.CharField(write_only=True, required=False)
    
    added_by = serializers.SerializerMethodField()

    class Meta:
        model = PatientVaccine
        fields = [
            "id",
            "vaccine_name",
            "vaccine_age",
            "created_at",
            "status",
            "is_completed",
            "completed_on",
            "completed_at",
            "due_date",
            "user",
            "patient",
            "vaccine_schedule",
            "patient_name",
            "custom_age",
            "due_date",
            "added_by"
        ]
        
    def get_added_by(self, obj):
        if obj.vaccine_schedule and obj.vaccine_schedule.user.is_staff:
            return "Admin"
        return getattr(obj.vaccine_schedule.user, "full_name", None) or obj.vaccine_schedule.user.email or "Unknown"

    def get_vaccine_name(self, obj):
        if obj.vaccine_schedule:
            return obj.vaccine_schedule.vaccine
        return obj.custom_vaccine

    def create(self, validated_data):
        custom_vaccine = validated_data.pop("custom_vaccine", None)
        custom_age = validated_data.pop("custom_age", "Custom")
        patient = validated_data["patient"]
        user = validated_data["user"]

        if custom_vaccine:
            account_type = "doctor" if user.account_type == "doctor" else "clinic"

            vaccine_schedule = VaccineSchedule.objects.create(
                doctor=user,
                account_type=account_type,
                patient=patient,
                age=custom_age,
                vaccine=custom_vaccine,
            )

            validated_data["vaccine_schedule"] = vaccine_schedule

            validated_data["custom_vaccine"] = custom_vaccine

        validated_data["patient"] = patient
        return super().create(validated_data)





class PatientSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(account_type="doctor"), required=False)
    doctor = serializers.PrimaryKeyRelatedField(queryset=ClinicDoctor.objects.all(), required=False)

    class Meta:
        model = Patient
        fields = [
            "id",
            "doctor",
            "user",
            "child_name",
            "date_of_birth",
            "mobile_number",
            "gender",
            "is_active",
            "created_at",
        ]

    def validate(self, data):
        request = self.context.get("request")
        user = request.user

        if data.get("doctor"):
            if not data["doctor"].is_active:
                raise serializers.ValidationError("This doctor is not active and cannot add patients.")
        elif user and user.account_type == "doctor":
            pass
        else:
            raise serializers.ValidationError(
                "Patient must be linked to either an individual doctor or a clinic doctor."
            )
        return data

    def create(self, validated_data):
        request = self.context.get("request")
        patient = Patient.objects.create(user=request.user, **validated_data)

        today = date.today()
        age_days = (today - patient.date_of_birth).days

        age_to_days = {
            "Birth": 0, "6 Weeks": 42, "10 Weeks": 70, "14 Weeks": 98,
            "6 Months": 183, "7 Months": 213, "9 Months": 274,
            "12 Months": 365, "15 Months": 456, "16–18 Months": 548,
            "18 Months": 548, "2 Years": 730, "3 Years": 1095,
            "4 Years": 1460, "4–6 Years": 2190, "5 Years": 1825,
            "6 Years": 2190, "7 Years": 2555, "8 Years": 2920,
            "10 Years": 3650, "16–18 Years": 6570,
        }

        for schedule in VaccineSchedule.objects.all():
            schedule_days = age_to_days.get(schedule.age, None)
            if schedule_days is None:
                continue

            due_date = patient.date_of_birth + timedelta(days=schedule_days)

            if age_days >= schedule_days:
                PatientVaccine.objects.create(
                    user=request.user, patient=patient, vaccine_schedule=schedule,
                    status="Completed", is_completed=True,
                    completed_on=today, completed_at="Other Private Hospital",
                    due_date=due_date,
                )
            else:
                status = "Pending" if today > due_date else "Upcoming"
                PatientVaccine.objects.create(
                    user=request.user, patient=patient, vaccine_schedule=schedule,
                    status=status, is_completed=False, due_date=due_date,
                )

        return patient


# ---------------- Daily Task to mark inactive ----------------
def mark_patients_inactive():
    overdue_vaccines = PatientVaccine.objects.filter(
        status="Pending",
        due_date__lt=timezone.now().date() - timedelta(days=7)
    )

    for vaccine in overdue_vaccines:
        vaccine.patient.is_active = False
        vaccine.patient.save()


class UpcomingPatientVaccineSerializer(serializers.ModelSerializer):
    patient = PatientSerializer(read_only=True)
    vaccine_name = serializers.CharField(source="vaccine_schedule.vaccine", read_only=True)
    vaccine_age = serializers.CharField(source="vaccine_schedule.age", read_only=True)
    due_date = serializers.DateField(format="%d-%b-%Y", read_only=True)

    class Meta:
        model = PatientVaccine
        fields = [
            "id",
            "vaccine_name",
            "vaccine_age",
            "due_date",
            "status",
            "is_completed",
            "patient",
        ]

