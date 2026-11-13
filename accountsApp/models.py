from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, email, raw_password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email).lower()
        extra_fields.setdefault("role", CustomUser.Role.STUDENT)
        user = self.model(email=email, **extra_fields)
        user.set_password(raw_password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, raw_password=None, **extra_fields):
        extra_fields.setdefault("role", CustomUser.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("account_status", CustomUser.AccountStatus.APPROVED)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, raw_password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        ADMIN = "ADMIN", "Administrator"

    class AccountStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    account_status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.PENDING,
        db_index=True,
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    @property
    def is_approved(self):
        return self.account_status == self.AccountStatus.APPROVED or self.role == self.Role.ADMIN


class AccountApproval(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="approval")
    status = models.CharField(
        max_length=20,
        choices=CustomUser.AccountStatus.choices,
        default=CustomUser.AccountStatus.PENDING,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_accounts",
        null=True,
        blank=True,
    )
    rejection_reason = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.status}"

    def approve(self, reviewer):
        self.status = CustomUser.AccountStatus.APPROVED
        self.reviewed_by = reviewer
        self.rejection_reason = ""
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "rejection_reason", "reviewed_at", "updated_at"])

        self.user.account_status = CustomUser.AccountStatus.APPROVED
        self.user.save(update_fields=["account_status"])

    def reject(self, reviewer, reason):
        self.status = CustomUser.AccountStatus.REJECTED
        self.reviewed_by = reviewer
        self.rejection_reason = reason
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "rejection_reason", "reviewed_at", "updated_at"])

        self.user.account_status = CustomUser.AccountStatus.REJECTED
        self.user.save(update_fields=["account_status"])


institutional_email_validator = RegexValidator(
    regex=r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.ac\.ke$",
    message="Only institutional student email addresses ending with .ac.ke are allowed.",
)
