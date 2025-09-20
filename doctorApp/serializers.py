from rest_framework import serializers
from authenticationApp.models import ClinicDoctor
from doctorApp.models import VaccineSchedule


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
    doctor_name = serializers.CharField(source="doctor.full_name", read_only=True)

    class Meta:
        model = VaccineSchedule
        fields = ["id", "doctor", "doctor_name", "account_type", "age", "vaccine"]
