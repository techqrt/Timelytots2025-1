from django.contrib import admin
from django.contrib.auth.models import Group
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from authenticationApp.models import User, ClinicDoctor

# Register your models here.

admin.site.register(User)
admin.site.register(ClinicDoctor)

for model in [Group, Token, BlacklistedToken, OutstandingToken]:
    try:
        admin.site.unregister(model)
    except admin.sites.NotRegistered:
        pass
