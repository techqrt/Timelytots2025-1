from django.urls import path
from doctorApp.views import ClinicDoctorViews, DoctorMarkActive, DoctorMarkInactive, VaccineScheduleViews, \
    AssignPatientVaccineView, VaccineReminderAPIView, FirebaseNotificationByDoctorView

urlpatterns = [
    path("clinic/doctor/", ClinicDoctorViews.as_view(), name="clinic_doctor"),
    path("clinic/doctor/<int:id>/", ClinicDoctorViews.as_view(), name="clinic_doctor"),

    path("clinic/doctor/mark/active/<int:id>/", DoctorMarkActive.as_view(), name="mark_active"),
    path("clinic/doctor/mark/inactive/<int:id>/", DoctorMarkInactive.as_view(), name="mark_inactive"),

    path("vaccine/schedule/", VaccineScheduleViews.as_view(), name="vaccine_schedule"),
    path("vaccine/schedule/<int:pk>/", VaccineScheduleViews.as_view(), name="vaccine_schedule"),

    path('add/patient/vaccines/', AssignPatientVaccineView.as_view(), name='assign-patient-vaccine'),
    path("patient/vaccines/<int:pk>/", AssignPatientVaccineView.as_view(), name="vaccine_schedule_detail"),
    
    path("send/vaccine/reminders/", VaccineReminderAPIView.as_view(), name="send-vaccine-reminders"),
]

