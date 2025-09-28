from django.shortcuts import render, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import models
from authenticationApp.models import ClinicDoctor
from doctorApp.models import VaccineSchedule
from doctorApp.serializers import ClinicDoctorSerializers, VaccineScheduleSerializer, CustomVaccineScheduleSerializer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from patientApp.models import Patient


# Create your views here.

class ClinicDoctorViews(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        try:
            serializer = ClinicDoctorSerializers(data=request.data, context={"request": request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        try:
            clinic_doctors = ClinicDoctor.objects.filter(clinic=request.user).order_by('-id')
            if not clinic_doctors.exists():
                return Response({'message': 'No doctors found.'}, status=status.HTTP_204_NO_CONTENT)

            serializer = ClinicDoctorSerializers(clinic_doctors, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, id):
        try:
            clinic_doctor = get_object_or_404(ClinicDoctor, id=id, clinic=request.user)
            serializer = ClinicDoctorSerializers(clinic_doctor)

            if clinic_doctor:
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, id):
        try:
            clinic_doctor = get_object_or_404(ClinicDoctor, id=id, clinic=request.user)
            serializer = ClinicDoctorSerializers(clinic_doctor, data=request.data, partial=True,
                                                 context={"request": request})

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, id):
        try:
            clinic_doctor = get_object_or_404(ClinicDoctor, id=id, clinic=request.user)
            clinic_doctor.delete()
            return Response({'message': f'{clinic_doctor.name} deleted successfully.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DoctorMarkActive(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def patch(self, request, id):
        try:
            clinic_doctor = get_object_or_404(ClinicDoctor, id=id, clinic=request.user)

            if not clinic_doctor.is_active:
                clinic_doctor.is_active = True
                clinic_doctor.save()
                return Response({'message': f'{clinic_doctor.name} marked as active'})
            else:
                return Response({'message': f'{clinic_doctor.name} is already active'})

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DoctorMarkInactive(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def patch(self, request, id):
        try:
            clinic_doctor = get_object_or_404(ClinicDoctor, id=id, clinic=request.user)

            if clinic_doctor.is_active:
                clinic_doctor.is_active = False
                clinic_doctor.save()
                return Response({'message': f'{clinic_doctor.name} marked as inactive'})
            else:
                return Response({'message': f'{clinic_doctor.name} is already inactive'})

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VaccineScheduleViews(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        schedules = VaccineSchedule.objects.filter(
            models.Q(user__isnull=True) | models.Q(user=request.user) | models.Q(user__is_staff=True)
        )
        serializer = VaccineScheduleSerializer(schedules, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if request.user.account_type not in ["doctor", "clinic"]:
            return Response(
                {"error": "Only doctors or clinics can add vaccine schedules."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data.copy()
        data["user"] = request.user.id
        data["account_type"] = request.user.account_type

        serializer = VaccineScheduleSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            schedule = VaccineSchedule.objects.get(pk=pk, user=request.user)
        except VaccineSchedule.DoesNotExist:
            return Response(
                {"error": "You can only update your own schedules."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = VaccineScheduleSerializer(schedule, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        try:
            schedule = VaccineSchedule.objects.get(pk=pk, user=request.user)
        except VaccineSchedule.DoesNotExist:
            return Response(
                {"error": "You can only update your own schedules."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = VaccineScheduleSerializer(schedule, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            schedule = VaccineSchedule.objects.get(pk=pk, user=request.user)
        except VaccineSchedule.DoesNotExist:
            return Response(
                {"error": "You can only delete your own schedules."},
                status=status.HTTP_404_NOT_FOUND,
            )

        schedule.delete()
        return Response({"message": "Schedule deleted successfully."}, status=status.HTTP_200_OK)
        
class AssignPatientVaccineView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, *args, **kwargs):
        serializer = CustomVaccineScheduleSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            vaccine_schedule = serializer.save()
            return Response({
                "id": vaccine_schedule.id,
                "user": vaccine_schedule.user.id,
                "patient": vaccine_schedule.patient.id,
                "patient_name": getattr(vaccine_schedule.patient, 'child_name', str(vaccine_schedule.patient)),
                "clinic_doctor": vaccine_schedule.clinic_doctor.id if vaccine_schedule.clinic_doctor else None,
                "doctor_name": vaccine_schedule.clinic_doctor.name if vaccine_schedule.clinic_doctor else "Clinic",
                "age": vaccine_schedule.age,
                "vaccine": vaccine_schedule.vaccine,
                "account_type": vaccine_schedule.account_type
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_object(self, pk):
        try:
            return VaccineSchedule.objects.get(pk=pk)
        except VaccineSchedule.DoesNotExist:
            return None

    def get(self, request, pk, *args, **kwargs):
        vaccine_schedule = self.get_object(pk)
        if not vaccine_schedule:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = CustomVaccineScheduleSerializer(vaccine_schedule, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk, *args, **kwargs):
        vaccine_schedule = self.get_object(pk)
        if not vaccine_schedule:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if vaccine_schedule.user.is_staff:
            return Response({"error": "You cannot edit vaccine schedules added by admin."}, status=status.HTTP_403_FORBIDDEN)

        serializer = CustomVaccineScheduleSerializer(
            vaccine_schedule,
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            updated = serializer.save()
            return Response({
                "id": updated.id,
                "patient": updated.patient.id if updated.patient else None,
                "patient_name": getattr(updated.patient, "child_name", str(updated.patient)) if updated.patient else None,
                "clinic_doctor": updated.clinic_doctor.id if updated.clinic_doctor else None,
                "doctor_name": updated.clinic_doctor.name if updated.clinic_doctor else None,
                "age": updated.age,
                "vaccine": updated.vaccine,
                "account_type": updated.account_type
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, *args, **kwargs):
        vaccine_schedule = self.get_object(pk)
        if not vaccine_schedule:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if vaccine_schedule.user.is_staff:
            return Response({"error": "You cannot delete vaccine schedules added by admin."}, status=status.HTTP_403_FORBIDDEN)

        vaccine_schedule.delete()
        return Response({"detail": "Deleted successfully."}, status=status.HTTP_204_NO_CONTENT)



