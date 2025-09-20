from django.shortcuts import render, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import models
from authenticationApp.models import ClinicDoctor
from doctorApp.models import VaccineSchedule
from doctorApp.serializers import ClinicDoctorSerializers, VaccineScheduleSerializer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


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

    # ---------- GET (List all schedules: global + own) ----------
    def get(self, request):
        schedules = VaccineSchedule.objects.filter(
            models.Q(doctor__isnull=True) | models.Q(doctor=request.user)
        )
        serializer = VaccineScheduleSerializer(schedules, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ---------- POST (Create new schedule: only doctor/clinic) ----------
    def post(self, request):
        if request.user.account_type not in ["doctor", "clinic"]:
            return Response(
                {"error": "Only doctors or clinics can add vaccine schedules."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data.copy()
        data["doctor"] = request.user.id
        data["account_type"] = request.user.account_type

        serializer = VaccineScheduleSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ---------- PUT / PATCH (Update only own schedules) ----------
    def put(self, request, pk):
        try:
            schedule = VaccineSchedule.objects.get(pk=pk, doctor=request.user)
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
            schedule = VaccineSchedule.objects.get(pk=pk, doctor=request.user)
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

    # ---------- DELETE (Delete only own schedules) ----------
    def delete(self, request, pk):
        try:
            schedule = VaccineSchedule.objects.get(pk=pk, doctor=request.user)
        except VaccineSchedule.DoesNotExist:
            return Response(
                {"error": "You can only delete your own schedules."},
                status=status.HTTP_404_NOT_FOUND,
            )

        schedule.delete()
        return Response({"message": "Schedule deleted successfully."}, status=status.HTTP_200_OK)
