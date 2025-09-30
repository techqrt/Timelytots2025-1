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
from datetime import date
import requests
from patientApp.models import Patient
from patientApp.models import PatientVaccine
from django.conf import settings
from collections import defaultdict
from rest_framework.permissions import IsAdminUser


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

            today = date.today()
            if vaccine_schedule.due_date:
                pv, created = PatientVaccine.objects.get_or_create(
                    patient=vaccine_schedule.patient,
                    vaccine_schedule=vaccine_schedule,
                    user=request.user,
                    defaults={"due_date": vaccine_schedule.due_date}
                )
                if created or pv.status != "Completed":
                    if today > vaccine_schedule.due_date:
                        pv.status = "Completed"
                        pv.is_completed = True
                        pv.completed_on = today
                        pv.completed_at = "Auto-generated"
                    elif today == vaccine_schedule.due_date:
                        pv.status = "Pending"
                        pv.is_completed = False
                    else:
                        pv.status = "Upcoming"
                        pv.is_completed = False
                    pv.save()

            return Response({
                "id": vaccine_schedule.id,
                "user": vaccine_schedule.user.id,
                "patient": vaccine_schedule.patient.id,
                "patient_name": getattr(vaccine_schedule.patient, 'child_name', str(vaccine_schedule.patient)),
                "clinic_doctor": vaccine_schedule.clinic_doctor.id if vaccine_schedule.clinic_doctor else None,
                "doctor_name": vaccine_schedule.clinic_doctor.name if vaccine_schedule.clinic_doctor else "Clinic",
                "age": vaccine_schedule.age,
                "due_date": vaccine_schedule.due_date,
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
            return Response({"error": "You cannot edit vaccine schedules added by admin."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = CustomVaccineScheduleSerializer(
            vaccine_schedule,
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            updated = serializer.save()

            today = date.today()
            if updated.due_date:
                pv, created = PatientVaccine.objects.get_or_create(
                    patient=updated.patient,
                    vaccine_schedule=updated,
                    user=request.user,
                    defaults={"due_date": updated.due_date}
                )
                if created or pv.status != "Completed":
                    if today > updated.due_date:
                        pv.status = "Completed"
                        pv.is_completed = True
                        pv.completed_on = today
                        pv.completed_at = "Auto-generated"
                    elif today == updated.due_date:
                        pv.status = "Pending"
                        pv.is_completed = False
                    else:
                        pv.status = "Upcoming"
                        pv.is_completed = False
                    pv.save()

            return Response({
                "id": updated.id,
                "patient": updated.patient.id if updated.patient else None,
                "patient_name": getattr(updated.patient, "child_name",
                                        str(updated.patient)) if updated.patient else None,
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
            return Response({"error": "You cannot delete vaccine schedules added by admin."},
                            status=status.HTTP_403_FORBIDDEN)

        vaccine_schedule.delete()
        return Response({"detail": "Deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

class VaccineReminderAPIView(APIView):
    # permission_classes = [IsAdminUser] 
    
    def post(self, request):
        try:
            today = date.today()

            due_vaccines = PatientVaccine.objects.filter(
                status__in=["Upcoming", "Pending"],
                is_completed=False,
                due_date=today
            ).select_related(
                "patient",
                "vaccine_schedule",
                "patient__doctor",
                "patient__user"
            )

            if not due_vaccines.exists():
                return Response({"message": "No vaccines due today."}, status=200)

            messages_sent = 0
            vaccines_by_patient = defaultdict(list)

            for vaccine in due_vaccines:
                vaccines_by_patient[vaccine.patient.id].append(vaccine)

            for patient_id, patient_vaccines in vaccines_by_patient.items():
                vaccine_names = ", ".join(
                    v.custom_vaccine or (v.vaccine_schedule.vaccine if v.vaccine_schedule else "")
                    for v in patient_vaccines
                )

                vaccine = patient_vaccines[0]
                child_name = vaccine.patient.child_name or ""
                due_date = vaccine.due_date.strftime("%d-%m-%Y")

                vaccine_schedule = ""
                if vaccine.vaccine_schedule:
                    if vaccine.vaccine_schedule.age:
                        vaccine_schedule = f"Age: {vaccine.vaccine_schedule.age}"
                    elif vaccine.vaccine_schedule.due_date:
                        vaccine_schedule = f"Date: {vaccine.vaccine_schedule.due_date.strftime('%d-%m-%Y')}"
                    else:
                        vaccine_schedule = "No schedule"

                doctor_name = "Doctor"
                if vaccine.patient.doctor:
                    if hasattr(vaccine.patient.doctor, "user") and vaccine.patient.doctor.user:
                        doctor_name = vaccine.patient.doctor.user.full_name
                elif hasattr(vaccine.patient, "user") and vaccine.patient.user:
                    doctor_name = vaccine.patient.user.full_name

                if vaccine.patient.doctor and vaccine.patient.doctor.clinic:
                    contact_number = vaccine.patient.doctor.clinic.clinic_contact_number or vaccine.patient.doctor.clinic.contact_number
                else:
                    contact_number = vaccine.patient.user.contact_number

                phone_number = vaccine.patient.mobile_number
                if not phone_number:
                    continue

                payload = {
                    "integrated_number": "918750138303",
                    "content_type": "template",
                    "payload": {
                        "messaging_product": "whatsapp",
                        "type": "template",
                        "template": {
                            "name": "vaccine_reminder1",
                            "language": {"code": "en", "policy": "deterministic"},
                            "namespace": "4e5add5b_52ed_4239_be4b_8b21e8a8f430",
                            "to_and_components": [
                                {
                                    "to": f"91{phone_number}",
                                    "components": {
                                        "body_1": {"type": "text", "value": child_name},
                                        "body_2": {"type": "text", "value": due_date},
                                        "body_3": {"type": "text", "value": vaccine_names},
                                        "body_4": {"type": "text", "value": vaccine_schedule},
                                        "body_5": {"type": "text", "value": doctor_name},
                                        "body_6": {"type": "text", "value": contact_number},
                                    },
                                }
                            ],
                        },
                    },
                }

                response = requests.post(
                    "https://api.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/",
                    headers={
                        "Content-Type": "application/json",
                        "authkey": settings.MSG91_AUTH_KEY,
                    },
                    json=payload,
                )

                if response.status_code == 200:
                    messages_sent += 1
                    VaccineReminderLog.objects.create(
                        user=vaccine.patient.user,
                        patient_name=child_name,
                        vaccine_name=vaccine_names
                    )


            return Response({"message": f"Vaccine reminders sent: {messages_sent}"}, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)


    



