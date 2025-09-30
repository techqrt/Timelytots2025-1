from django.urls import path
from .views import PatientCountView, UpcomingAppointmentsCountView, UserVaccineMessageCountView, CompletedByAdminDoctorCountAPIView

urlpatterns = [
    path("total/count/", PatientCountView.as_view(), name="patient_count"),
    path("upcoming/appointments/count/", UpcomingAppointmentsCountView.as_view(), name="upcoming_appointments_count"),
    path("message/count/", UserVaccineMessageCountView.as_view(), name="message_count"),
    path("complete/count/", CompletedByAdminDoctorCountAPIView.as_view(), name="complete_count"),

]

