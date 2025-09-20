from django.urls import path
from patientApp.views import PatientViews, PatientMarkActive, PatientMarkInactive, PatientSearch, \
    PatientVaccineViews, MarkVaccineCompletedView, MarkVaccinePendingView, VaccineSearch, UpcomingAppointmentsView, \
    CreatePatientVaccineView

urlpatterns = [
    path("patient/", PatientViews.as_view(), name="patient"),
    path("patient/<int:id>/", PatientViews.as_view(), name="patient"),

    path("patient/search/", PatientSearch.as_view(), name="patient_search"),

    path("patient/mark/active/<int:id>/", PatientMarkActive.as_view(), name="mark_active"),
    path("patient/mark/inactive/<int:id>/", PatientMarkInactive.as_view(), name="mark_inactive"),

    path("patient/vaccine/", PatientVaccineViews.as_view(), name="patient_vaccine"),
    path("patient/vaccine/<int:id>/", PatientVaccineViews.as_view(), name="patient_vaccine"),

    path("patient/vaccine/complete/<int:pk>/", MarkVaccineCompletedView.as_view(), name="mark-vaccine-complete"),
    path("patient/vaccine/pending/<int:pk>/", MarkVaccinePendingView.as_view(), name="mark-vaccine-pending"),

    path('vaccine/search/', VaccineSearch.as_view(), name='search'),

    path('upcoming/appointments/', UpcomingAppointmentsView.as_view(), name='upcoming_appointments'),

    path("add/patient/vaccines/<int:patient_id>/", CreatePatientVaccineView.as_view(), name="create_vaccine"),

]

