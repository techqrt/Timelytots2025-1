from datetime import date
from django.shortcuts import render, get_object_or_404
from rest_framework import serializers, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import models
from doctorApp.models import VaccineSchedule
from doctorApp.utils import send_whatsapp_template, send_registered_whatsapp
from patientApp.models import Patient, PatientVaccine
from rest_framework import status
from patientApp.serializers import PatientSerializer, PatientVaccineSerializer, UpcomingPatientVaccineSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import timedelta

# Create your views here.

class PatientViews(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get(self, request):
        try:
            patients = Patient.objects.filter(user=request.user).order_by('-id')
            if not patients.exists():
                return Response({'message': 'no patients found.'}, status=status.HTTP_204_NO_CONTENT)

            response_data = []
            today = date.today()

            for patient in patients:
                schedules = VaccineSchedule.objects.filter(models.Q(patient=patient) | models.Q(user__is_staff=True))

                for schedule in schedules:
                    due_date = schedule.due_date

                    if due_date is None:
                        continue

                    pv, created = PatientVaccine.objects.get_or_create(
                        patient=patient,
                        vaccine_schedule=schedule,
                        user=request.user,
                        defaults={"due_date": due_date}
                    )

                    if created or pv.status != "Completed":
                        if today > due_date:
                            pv.status = "Completed"
                            pv.is_completed = True
                            pv.completed_on = today
                            pv.completed_at = "Auto-generated"
                        elif today == due_date:
                            pv.status = "Pending"
                            pv.is_completed = False
                        else:
                            pv.status = "Upcoming"
                            pv.is_completed = False
                        pv.save()

                vaccines = PatientVaccine.objects.filter(patient=patient, user=request.user).order_by("vaccine_schedule__age_order")

                response_data.append({
                    "patient": PatientSerializer(patient).data,
                    "Completed": PatientVaccineSerializer(vaccines.filter(status="Completed"), many=True).data,
                    "Upcoming": PatientVaccineSerializer(vaccines.filter(status="Upcoming"), many=True).data,
                    "Pending": PatientVaccineSerializer(vaccines.filter(status="Pending"), many=True).data,
                })

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, id):
        try:
            patient = get_object_or_404(Patient, id=id, user=request.user)
            today = date.today()

            schedules = VaccineSchedule.objects.filter(models.Q(patient=patient) | models.Q(user__is_staff=True))

            for schedule in schedules:
                due_date = schedule.due_date
                if due_date is None:
                    continue

                pv, created = PatientVaccine.objects.get_or_create(
                    patient=patient,
                    vaccine_schedule=schedule,
                    user=request.user,
                    defaults={"due_date": due_date}
                )

                if created or pv.status != "Completed":
                    if today > due_date:
                        pv.status = "Completed"
                        pv.is_completed = True
                        pv.completed_on = today
                        pv.completed_at = "Auto-generated"
                    elif today == due_date:
                        pv.status = "Pending"
                        pv.is_completed = False
                    else:
                        pv.status = "Upcoming"
                        pv.is_completed = False
                    pv.save()

            vaccines = PatientVaccine.objects.filter(patient=patient, user=request.user)

            categorized = {
                "Completed": PatientVaccineSerializer(vaccines.filter(status="Completed"), many=True).data,
                "Upcoming": PatientVaccineSerializer(vaccines.filter(status="Upcoming"), many=True).data,
                "Pending": PatientVaccineSerializer(vaccines.filter(status="Pending"), many=True).data,
            }

            return Response({
                "patient": PatientSerializer(patient).data,
                "vaccines": categorized
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def post(self, request):
        try:
            serializer = PatientSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                patient = serializer.save()
    
                today = date.today()
                schedules = VaccineSchedule.objects.filter(models.Q(patient=patient) | models.Q(user__is_staff=True))
    
                for schedule in schedules:
                    due_date = schedule.due_date
                    if due_date is None:
                        continue
    
                    pv, created = PatientVaccine.objects.get_or_create(
                        patient=patient,
                        vaccine_schedule=schedule,
                        user=request.user,
                        defaults={"due_date": due_date}
                    )
    
                    if created or pv.status != "Completed":
                        if today > due_date:
                            pv.status = "Completed"
                            pv.is_completed = True
                            pv.completed_on = today
                            pv.completed_at = "Auto-generated"
                        elif today == due_date:
                            pv.status = "Pending"
                            pv.is_completed = False
                        else:
                            pv.status = "Upcoming"
                            pv.is_completed = False
                        pv.save()
    
                user = request.user
                if user.account_type == "doctor":
                    doctor_name = user.full_name
                elif user.account_type == "clinic":
                    if patient.doctor:
                        doctor_name = patient.doctor.name
                    else:
                        doctor_name = "Doctor"
                else:
                    doctor_name = "Doctor"
    
                send_registered_whatsapp(
                    mobile_number=patient.mobile_number,
                    child_name=patient.child_name,
                    doctor_name=doctor_name,
                    dob=patient.date_of_birth
                )
    
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
        except Exception as e:
            import traceback
            print("Error in post method:", e)
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



    def patch(self, request, id):
        try:
            patient = get_object_or_404(Patient, id=id, user=request.user)
            serializers = PatientSerializer(
                patient,
                partial=True,
                data=request.data,
                context={"request": request}   
            )
    
            if serializers.is_valid():
                serializers.save()
                return Response(serializers.data, status=status.HTTP_200_OK)  
    
            else:
                return Response(serializers.errors, status=status.HTTP_400_BAD_REQUEST)
    
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def delete(self, request, id):
        try:
            patient = get_object_or_404(Patient, id=id, user=request.user)

            if patient:
                patient.delete()
                return Response({'message': 'patient deleted successfully'}, status=status.HTTP_200_OK)

            else:
                return Response({'message': 'no patients found.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PatientSearch(APIView):
    def get(self, request):
        try:
            query = request.query_params.get('search', '')
            patient = Patient.objects.filter(child_name__icontains=query) | Patient.objects.filter(
                mobile_number__icontains=query)

            if patient:
                serializers = PatientSerializer(patient, many=True)
                return Response(serializers.data, status=status.HTTP_200_OK)

            else:
                return Response({'message': 'No patient found'}, status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PatientMarkActive(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def patch(self, request, id):
        try:
            patient = get_object_or_404(Patient, id=id, user=request.user)

            if not patient.is_active:
                patient.is_active = True
                patient.save()
                return Response({'message': f'{patient.child_name} marked as active'})
            else:
                return Response({'message': f'{patient.child_name} is already active'})

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PatientMarkInactive(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def patch(self, request, id):
        try:
            patient = get_object_or_404(Patient, id=id, user=request.user)

            if patient.is_active:
                patient.is_active = False
                patient.save()
                return Response({'message': f'{patient.child_name} marked as inactive'})
            else:
                return Response({'message': f'{patient.child_name} is already inactive'})

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PatientVaccineViews(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        try:
            patient_vaccines = PatientVaccine.objects.filter(user=request.user).order_by('vaccine_schedule__age_order')

            if patient_vaccines:
                serializers = PatientVaccineSerializer(patient_vaccines, many=True)
                return Response(serializers.data, status=status.HTTP_200_OK)

            else:
                return Response({'message': 'no patients vaccine found.'}, status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, id):
        try:
            patient_vaccines = get_object_or_404(PatientVaccine, id=id, user=request.user)

            if patient_vaccines:
                serializers = PatientVaccineSerializer(patient_vaccines)
                return Response(serializers.data, status=status.HTTP_200_OK)

            else:
                return Response({'message': 'no patients vaccine found.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MarkVaccineCompletedView(generics.UpdateAPIView):
    serializer_class = PatientVaccineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PatientVaccine.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        try:
            vaccine = self.get_object()

            if vaccine.is_completed:
                return Response(
                    {"message": "This vaccine is already marked as completed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            completed_at = request.data.get("completed_at")
            valid_sources = [src for src, _ in PatientVaccine.COMPLETION_SOURCE]
            if completed_at not in valid_sources:
                return Response(
                    {"error": f"Invalid completion source. Must be one of {valid_sources}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            vaccine.is_completed = True
            vaccine.status = "Completed"
            vaccine.completed_on = date.today()
            vaccine.completed_at = completed_at
            vaccine.save()

            serializer = self.get_serializer(vaccine)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Something went wrong: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MarkVaccinePendingView(generics.UpdateAPIView):
    serializer_class = PatientVaccineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PatientVaccine.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        try:
            vaccine = self.get_object()

            if not vaccine.is_completed and vaccine.status == "Pending":
                return Response(
                    {"message": "This vaccine is already pending."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            vaccine.is_completed = False
            vaccine.status = "Pending"
            vaccine.completed_on = None
            vaccine.completed_at = None
            vaccine.save()

            serializer = self.get_serializer(vaccine)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Something went wrong: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VaccineSearch(APIView):
    def get(self, request):
        try:
            query = request.query_params.get('search', '')
            vaccine = VaccineSchedule.objects.filter(age__icontains=query) | VaccineSchedule.objects.filter(
                vaccine__icontains=query)

            if vaccine:
                serializers = VaccineSchedule(vaccine, many=True)
                return Response(serializers.data, status=status.HTTP_200_OK)

            else:
                return Response({'message': 'No vaccine found'}, status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpcomingAppointmentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            today = date.today()
            next_30_days = today + timedelta(days=30)

            upcoming_appointments = PatientVaccine.objects.filter(
                user=request.user,
                status="Upcoming",
                is_completed=False,
                due_date__range=[today, next_30_days],
                patient__is_active=True  # ✅ Only include active patients
            ).order_by("due_date")

            if upcoming_appointments.exists():
                serializer = UpcomingPatientVaccineSerializer(upcoming_appointments, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"message": "No upcoming appointments found in the next 30 days."},
                    status=status.HTTP_204_NO_CONTENT
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



