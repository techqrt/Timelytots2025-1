from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


# ---------------- Custom User Manager ----------------
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


# ---------------- User Model ----------------
class User(AbstractBaseUser, PermissionsMixin):
    ACCOUNT_TYPE_CHOICES = [
        ("doctor", "Individual Doctor"),
        ("clinic", "Clinic / Hospital"),
    ]

    BILLING_METHOD = [
        ('Per Message', 'Per Message'),
        ('Monthly Subscription', 'Monthly Subscription'),
        ('Per Message + Monthly Subscription', 'Per Message + Monthly Subscription'),
    ]

    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    full_name = models.CharField(max_length=200)
    contact_number = models.CharField(max_length=15)
    clinic_contact_number = models.CharField(max_length=15, blank=True, null=True)
    specialty = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(unique=True)
    address = models.TextField(blank=True, null=True)
    terms_accepted = models.BooleanField(default=False)
    fcm_token = models.TextField(blank=True, null=True, default="dDAd6XyCTyO4nCHxCXjMg1:APA91bFjRTx30KfuaWcXbi0voEtwwb2jVzcXttr_QsgMR64cx7LKzxqI2xZVOXyM3UCus4145-1n-TErc-p9qZmF6Uzhn5AvTaKgi_GbSNMzWMuNpb83WWU")

    billing_method = models.CharField(choices=BILLING_METHOD, max_length=155, blank=True, null=True)
    monthly_subscription_fees = models.PositiveIntegerField(blank=True, null=True)
    per_message_charges = models.PositiveIntegerField(blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.email} ({self.account_type})"


# ---------------- Clinic Doctor Model ----------------
class ClinicDoctor(models.Model):
    clinic = models.ForeignKey(User, on_delete=models.CASCADE, related_name="clinic_doctors")
    speciality = models.CharField(max_length=255)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.clinic.full_name})"
