from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from applicationsApp.models import BursaryApplication


class ApplicationPeriod(models.Model):
    name = models.CharField(max_length=120, unique=True)
    opens_on = models.DateField()
    closes_on = models.DateField()
    verification_date = models.DateField(null=True, blank=True)
    award_announcement_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class BursaryOpportunity(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    application_period = models.ForeignKey(ApplicationPeriod, on_delete=models.PROTECT, related_name="opportunities")
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class EligibilityCriteria(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    weight = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Eligibility criteria"

    def __str__(self):
        return self.name


class BursaryBudget(models.Model):
    academic_year = models.CharField(max_length=20, unique=True)
    total_budget = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    allocated_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    disbursed_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def remaining_balance(self):
        return self.total_budget - self.allocated_amount

    def __str__(self):
        return f"{self.academic_year} Budget"


class BursaryAward(models.Model):
    application = models.OneToOneField(BursaryApplication, on_delete=models.PROTECT, related_name="award")
    amount_requested = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    amount_approved = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    assessment_score = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)])
    approval_date = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    reason_for_allocation = models.TextField()
    budget = models.ForeignKey(BursaryBudget, on_delete=models.PROTECT, related_name="awards")

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.amount_approved > self.budget.remaining_balance:
            raise ValidationError("Approved amount exceeds available bursary budget.")

    def __str__(self):
        return f"Award {self.application.reference_number}"
