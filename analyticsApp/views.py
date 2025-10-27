from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from datetime import date, timedelta
from patientApp.models import PatientVaccine
from patientApp.models import Patient 
import calendar
from datetime import datetime
from patientApp.models import PatientVaccine
from doctorApp.models import ReminderLog




class PatientCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:

            total_patients = Patient.objects.filter(user=request.user, is_active=True).count()

            return Response({"total_patients": total_patients}, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            
class UpcomingAppointmentsCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            today = date.today()
            next_30_days = today + timedelta(days=30)

            next_30_days_count = PatientVaccine.objects.filter(
                user=request.user,
                status="Upcoming",
                is_completed=False,
                due_date__range=[today, next_30_days],
                patient__is_active=True
            ).count()

            month = request.query_params.get("month", None)
            year = request.query_params.get("year", None)
            custom_month_count = None

            if month and month.lower() != "all":
                month = int(month)
                if year and year.isdigit():
                    year = int(year)
                else:
                    year = today.year

                start_date = date(year, month, 1)
                last_day = calendar.monthrange(year, month)[1]
                end_date = date(year, month, last_day)

                custom_month_count = PatientVaccine.objects.filter(
                    user=request.user,
                    status="Upcoming",
                    is_completed=False,
                    due_date__range=[start_date, end_date],
                    patient__is_active=True
                ).count()

            return Response({
                "user": request.user.full_name,
                "month": month if month else "All",
                "year": year if year else "All",
                "next_30_days_count": next_30_days_count,
                "custom_month_count": custom_month_count
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
class UserVaccineMessageCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            month = request.GET.get("month")
            year = request.GET.get("year")

            logs = ReminderLog.objects.filter(user=user)

            if month and month.lower() != "all":
                logs = logs.filter(sent_at__month=int(month))
            if year and year.lower() != "all":
                logs = logs.filter(sent_at__year=int(year))

            return Response({
                "user": user.full_name,
                "month": month or "All",
                "year": year or "All",
                "message_count": logs.count()
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)
            
class CompletedByAdminDoctorCountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            month = request.GET.get("month")
            year = request.GET.get("year")

            vaccines = PatientVaccine.objects.filter(
                user=user,
                is_completed=True,
                completed_at="Admin Doctor"
            )

            if month and month.lower() != "all":
                vaccines = vaccines.filter(completed_on__month=int(month))
            if year and year.lower() != "all":
                vaccines = vaccines.filter(completed_on__year=int(year))

            return Response({
                "user": user.full_name,
                "month": month or "All",
                "year": year or "All",
                "completed_count": vaccines.count()
            })

        except Exception as e:
            return Response({"error": str(e)}, status=500)
