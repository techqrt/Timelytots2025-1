from datetime import date
from django.shortcuts import render, get_object_or_404
from rest_framework import serializers, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from doctorApp.models import VaccineSchedule
from doctorApp.utils import send_whatsapp_template, send_whatsapp_reminder
from patientApp.models import Patient, PatientVaccine
from rest_framework import status
from patientApp.serializers import PatientSerializer, PatientVaccineSerializer, UpcomingPatientVaccineSerializer
from rest_framework.views import APIView
from rest_framework.response import Response


# Create your views here.

class PatientViews(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        try:
            serializer = PatientSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                patient = serializer.save()

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

                send_whatsapp_reminder(
                    mobile_number=patient.mobile_number,
                    child_name=patient.child_name,
                    doctor_name=doctor_name
                )

                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            import traceback
            print("Error in post method:", e)
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        try:
            patients = Patient.objects.filter(user=request.user).order_by('-id')

            if not patients.exists():
                return Response({'message': 'no patients found.'}, status=status.HTTP_204_NO_CONTENT)

            response_data = []
            for patient in patients:
                vaccines = PatientVaccine.objects.filter(patient=patient)

                categorized = {
                    "Completed": PatientVaccineSerializer(vaccines.filter(status="Completed"), many=True).data,
                    "Upcoming": PatientVaccineSerializer(vaccines.filter(status="Upcoming"), many=True).data,
                    "Pending": PatientVaccineSerializer(vaccines.filter(status="Pending"), many=True).data,
                }

                response_data.append({
                    "patient": PatientSerializer(patient).data,
                    "vaccines": categorized
                })

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, id):
        try:
            patient = get_object_or_404(Patient, id=id, user=request.user)

            vaccines = PatientVaccine.objects.filter(patient=patient)

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

    def patch(self, request, id):
        try:
            patient = get_object_or_404(Patient, id=id, user=request.user)
            serializers = PatientSerializer(patient, partial=True, data=request.data)

            if serializers.is_valid():
                serializers.save()
                return Response(serializers.data, status=status.HTTP_201_CREATED)

            else:
                return Response({'message': 'no patients found.'}, status=status.HTTP_404_NOT_FOUND)

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
            patient_vaccines = PatientVaccine.objects.filter(user=request.user).order_by('-id')

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
            upcoming_appointments = PatientVaccine.objects.filter(
                user=request.user,
                status="Upcoming",
                is_completed=False,
                due_date__gte=today
            ).order_by("due_date")

            if upcoming_appointments.exists():
                serializer = UpcomingPatientVaccineSerializer(upcoming_appointments, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response({"message": "No upcoming appointments found."}, status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreatePatientVaccineView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, patient_id):
        patient = get_object_or_404(Patient, id=patient_id)
        vaccines = PatientVaccine.objects.filter(patient=patient)
        serializer = PatientVaccineSerializer(vaccines, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        patient = get_object_or_404(Patient, id=patient_id)

        data = request.data.copy()
        data["user"] = request.user.id
        data["patient"] = patient.id

        serializer = PatientVaccineSerializer(data=data)
        if serializer.is_valid():
            if not serializer.validated_data.get("vaccine_schedule") and not serializer.validated_data.get("custom_vaccine"):
                return Response(
                    {"error": "Provide either vaccine_schedule or custom_vaccine"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        patient_vaccine = get_object_or_404(PatientVaccine, pk=pk, user=request.user)

        serializer = PatientVaccineSerializer(patient_vaccine, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        patient_vaccine = get_object_or_404(PatientVaccine, pk=pk, user=request.user)
        patient_vaccine.delete()
        return Response({"message": "Patient vaccine entry deleted."}, status=status.HTTP_200_OK)
