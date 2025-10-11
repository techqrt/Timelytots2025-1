from rest_framework import serializers
from authenticationApp.models import ClinicDoctor, User
from doctorApp.models import VaccineSchedule, FirebaseNotificationLog
from patientApp.models import PatientVaccine, Patient


class ClinicDoctorSerializers(serializers.ModelSerializer):
    class Meta:
        model = ClinicDoctor
        fields = ["id", "name", "speciality", "is_active"]
        extra_kwargs = {
            "is_active": {"required": False}
        }

    def create(self, validated_data):
        request = self.context.get("request")
        return ClinicDoctor.objects.create(clinic=request.user, **validated_data)


class VaccineScheduleSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="user.full_name", read_only=True)
    added_by = serializers.SerializerMethodField()

    class Meta:
        model = VaccineSchedule
        fields = ["id", "user", "doctor_name", "account_type", "age", "vaccine", "added_by"]

    def get_added_by(self, obj):
        if obj.user and obj.user.is_staff:
            return "Admin"
        elif obj.user:
            return obj.user.full_name or obj.user.username
        return "System"


class CustomVaccineScheduleSerializer(serializers.ModelSerializer):
    patient_id = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.all(), write_only=True
    )
    clinic_doctor_id = serializers.PrimaryKeyRelatedField(
        queryset=ClinicDoctor.objects.all(), write_only=True, required=False, allow_null=True
    )

    patient_name = serializers.CharField(source="patient.name", read_only=True)
    patient = serializers.IntegerField(source="patient.id", read_only=True) 
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = VaccineSchedule
        fields = [
            "id",
            "user",
            "patient",           
            "patient_name",     
            "clinic_doctor",
            "doctor_name",
            "age",
            "due_date",
            "vaccine",
            "account_type",
            "patient_id",       
            "clinic_doctor_id", 
        ]
        read_only_fields = ["id", "user", "clinic_doctor", "account_type"]

    def get_doctor_name(self, obj):
        return obj.clinic_doctor.name if obj.clinic_doctor else "Clinic"

    def create(self, validated_data):
        user = self.context["request"].user
        patient = validated_data.pop("patient_id")
        clinic_doctor = validated_data.pop("clinic_doctor_id", None)
        schedule = VaccineSchedule.objects.create(
            user=user,
            patient=patient,
            clinic_doctor=clinic_doctor,
            account_type=user.account_type,
            **validated_data
        )
        return schedule

    def update(self, instance, validated_data):
        if "patient_id" in validated_data:
            instance.patient = validated_data.pop("patient_id")
        if "clinic_doctor_id" in validated_data:
            instance.clinic_doctor = validated_data.pop("clinic_doctor_id")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance



class FirebaseNotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FirebaseNotificationLog
        fields = [
            "id",
            "doctor_id",
            "patient_id",
            "title",
            "body",
            "status",
            "data",
            "response",
            "created_at",
        ]