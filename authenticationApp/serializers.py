from timelytots.settings import DEFAULT_FROM_EMAIL
from django.core.mail import send_mail
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.tokens import default_token_generator

from .models import User, ClinicDoctor
from django.utils.encoding import force_bytes
import random, string
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from timelytots import settings
from .models import PasswordResetCode

class ClinicDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicDoctor
        fields = ["id", "name", "speciality", "is_active"]


class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    clinic_doctors = ClinicDoctorSerializer(many=True, required=False)

    class Meta:
        model = User
        fields = [
            "account_type",
            "full_name",
            "contact_number",
            "clinic_contact_number",
            "specialty",
            "email",
            "password",
            "address",
            "terms_accepted",
            "clinic_doctors",
        ]

    def create(self, validated_data):
        clinic_doctors_data = validated_data.pop("clinic_doctors", [])
        password = validated_data.pop("password")

        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        if user.account_type == "clinic":
            for doc in clinic_doctors_data:
                ClinicDoctor.objects.create(clinic=user, **doc)
        
        self.send_welcome_email(user, clinic_doctors_data)

        return user

    # ---------------- Send Welcome Email ----------------
    def send_welcome_email(self, user, clinic_doctors):
        context = {
            "account_type": user.account_type,
            "full_name": user.full_name,
            "clinic_name": user.full_name if user.account_type == "clinic" else None,
            "clinic_doctors": clinic_doctors,
            "dashboard_link": "https://timelytots.com/dashboard",
            "help_link": "https://timelytots.com/help",
            "download_link": "https://play.google.com/store/apps/details?id=com.timelytots",
            "current_year": 2025,
        }

        if user.account_type == "doctor":
            subject = f"Welcome to Timely Tots, Dr. {user.full_name}!"
        else:
            subject = f"Welcome to Timely Tots — {user.full_name} is ready!"

        html_body = render_to_string("emails/welcome_timelytots.html", context)
        text_body = render_to_string("emails/welcome_timelytots.txt", context)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)

class UserLoginSerializers(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            email = data['email']
            password = data['password']

            if User.objects.filter(email=email).exists():
                user = User.objects.get(email=email)

                if user.check_password(password):
                    refresh = RefreshToken.for_user(user)

                    return {
                        'user_id': user.id,
                        'access_token': str(refresh.access_token),
                        'refresh_token': str(refresh)
                    }

                else:
                    raise serializers.ValidationError('Incorrect password!')

            else:
                raise serializers.ValidationError('Email not found!')

        except Exception as e:
            raise serializers.ValidationError(str(e))


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=6, write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New password and confirm password do not match.")
        if data['old_password'] == data['new_password']:
            raise serializers.ValidationError("New password must differ from old password.")
        return data

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No account found with this email.")
        return value

    def generate_reset_code(self, length=6):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    def save(self):
        user = User.objects.get(email=self.validated_data["email"])
        reset_code = self.generate_reset_code()

        PasswordResetCode.objects.create(user=user, code=reset_code)

        subject = "Reset Your Password - Timely Tots"
        message = f"""
                Hi {user.full_name},
                
                You requested to reset your password for your Timely Tots account.
                
                Your password reset code is: {reset_code}
                
                Please enter this code in the app or website to set your new password.
                
                If you did not request this, please ignore this email.
                """
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
        return {"message": "Password reset code sent to your email."}


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField(max_length=10)
    new_password = serializers.CharField(min_length=6)
    confirm_password = serializers.CharField(min_length=6)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match.")

        try:
            user = User.objects.get(email=data["email"])
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this email.")

        try:
            reset_code = PasswordResetCode.objects.get(user=user, code=data["token"])
        except PasswordResetCode.DoesNotExist:  
            raise serializers.ValidationError("Invalid or expired reset code.")

        self.user = user
        self.reset_code = reset_code
        return data

    def save(self):
        self.user.set_password(self.validated_data["new_password"])
        self.user.save()

        self.reset_code.delete()
        return self.user



class UserSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'




class ProfileSerializer(serializers.ModelSerializer):
    clinic_doctors = serializers.SerializerMethodField()

    class Meta:
        model = User
        exclude = [
            "password",
            "is_superuser",
            "is_staff",
            "is_active",
            "groups",
            "user_permissions",
        ]

    def get_clinic_doctors(self, obj):
        if obj.account_type == "clinic":
            return ClinicDoctorSerializer(obj.clinic_doctors.all(), many=True).data
        return None
