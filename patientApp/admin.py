from django.contrib import admin
from patientApp.models import Patient, PatientVaccine

# Register your models here.

admin.site.register(Patient)
admin.site.register(PatientVaccine)

admin.site.site_header = "TimelyTots"
admin.site.site_title = "The Future of Pediatric Care is Here."
admin.site.index_title = "Focus on Care, Not Calendars."
