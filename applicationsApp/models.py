from uuid import uuid4

from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models

from studentsApp.models import Institution, StudentProfile


class BursaryApplication(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        VERIFICATION_REQUIRED = "VERIFICATION_REQUIRED", "Verification Required"
        VERIFIED = "VERIFIED", "Verified"
        APPROVED = "APPROVED", "Approved"
        PARTIALLY_AWARDED = "PARTIALLY_AWARDED", "Partially Awarded"
        REJECTED = "REJECTED", "Rejected"
        WAITLISTED = "WAITLISTED", "Waitlisted"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications")
    student_profile = models.ForeignKey(StudentProfile, on_delete=models.SET_NULL, null=True, blank=True)
    reference_number = models.CharField(max_length=32, unique=True, db_index=True)
    academic_year = models.CharField(max_length=20)
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT)
    course = models.CharField(max_length=255)
    qualification = models.CharField(max_length=30)
    year_of_study = models.PositiveSmallIntegerField()
    admission_number = models.CharField(max_length=100)
    institution_location = models.CharField(max_length=255)

    annual_household_income = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    number_of_dependants = models.PositiveIntegerField(default=0)
    other_sources_of_financial_support = models.TextField(blank=True)
    previous_bursary_awards = models.TextField(blank=True)
    amount_requested = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    financial_need_explanation = models.TextField()
    declaration_accepted = models.BooleanField(default=False)

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT, db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "academic_year"], name="uniq_student_application_year"),
        ]
        indexes = [
            models.Index(fields=["student", "status"]),
            models.Index(fields=["academic_year", "status"]),
        ]

    def __str__(self):
        return f"{self.reference_number} - {self.student.full_name}"

    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = f"NGCDF-{uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)


class ApplicationDocument(models.Model):
    class DocumentType(models.TextChoices):
        NATIONAL_ID = "NATIONAL_ID", "National ID Copy"
        ADMISSION_LETTER = "ADMISSION_LETTER", "Admission Letter"
        FEE_STRUCTURE = "FEE_STRUCTURE", "Fee Structure"
        FEE_STATEMENT = "FEE_STATEMENT", "Fee Statement"
        TRANSCRIPT = "TRANSCRIPT", "Academic Transcript"
        GUARDIAN_ID = "GUARDIAN_ID", "Parent/Guardian Identification"
        DEATH_CERTIFICATE = "DEATH_CERTIFICATE", "Death Certificate"
        OTHER = "OTHER", "Other Supporting Document"

    application = models.ForeignKey(BursaryApplication, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    file = models.FileField(
        upload_to="application_documents/",
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "jpg", "jpeg", "png"])],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)


class ApplicationStatusHistory(models.Model):
    application = models.ForeignKey(BursaryApplication, on_delete=models.CASCADE, related_name="status_history")
    previous_status = models.CharField(max_length=30, choices=BursaryApplication.Status.choices)
    new_status = models.CharField(max_length=30, choices=BursaryApplication.Status.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]


class ApplicationAssessment(models.Model):
    application = models.OneToOneField(BursaryApplication, on_delete=models.CASCADE, related_name="assessment")
    criteria_snapshot = models.JSONField(default=dict)
    score = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)])
    assessed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True)
    assessed_at = models.DateTimeField(auto_now_add=True)


class Appeal(models.Model):
    application = models.ForeignKey(BursaryApplication, on_delete=models.CASCADE, related_name="appeals")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="appeals")
    reason = models.TextField()
    supporting_evidence = models.FileField(upload_to="appeals/", blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[("PENDING", "Pending"), ("REVIEWED", "Reviewed"), ("RESOLVED", "Resolved")],
        default="PENDING",
    )
    resolution_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_appeals",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ConflictOfInterest(models.Model):
    application = models.ForeignKey(BursaryApplication, on_delete=models.CASCADE, related_name="conflicts")
    administrator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="declared_conflicts")
    reason = models.TextField()
    declared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["application", "administrator"], name="uniq_application_admin_conflict"),
        ]
