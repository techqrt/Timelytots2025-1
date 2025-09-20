from django.conf.global_settings import DEFAULT_FROM_EMAIL
from django.core.mail import send_mail
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.tokens import default_token_generator

from .models import User, ClinicDoctor
from django.utils.encoding import force_bytes


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

        return user


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

    def save(self):
        user = User.objects.get(email=self.validated_data['email'])
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_link = f"http://127.0.0.1:8000/reset-password/{uid}/{token}/"

        subject = "Reset Your Password"
        message = f"Hi {user.full_name},\n\nClick the link below to reset your password:\n{reset_link}\n\nIf you did not request this, please ignore this email."
        from_email = DEFAULT_FROM_EMAIL
        recipient_list = [user.email]

        send_mail(subject, message, from_email, recipient_list, fail_silently=False)

        return {"message": "Password reset link sent to your email."}


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=6)
    confirm_password = serializers.CharField(min_length=6)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")

        try:
            uid = force_str(urlsafe_base64_decode(data['uid']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid UID.")

        if not default_token_generator.check_token(user, data['token']):
            raise serializers.ValidationError("Token is invalid or expired.")

        self.user = user
        return data

    def save(self):
        self.user.set_password(self.validated_data['new_password'])
        self.user.save()
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
