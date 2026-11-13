from django.conf import settings
from django.db import models


class Institution(models.Model):
    class InstitutionType(models.TextChoices):
        UNIVERSITY = "UNIVERSITY", "University"
        COLLEGE = "COLLEGE", "College"

    name = models.CharField(max_length=255, unique=True)
    institution_type = models.CharField(max_length=20, choices=InstitutionType.choices)
    county = models.CharField(max_length=120, blank=True)
    constituency = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return self.name


class StudentProfile(models.Model):
    class Qualification(models.TextChoices):
        BACHELORS = "BACHELORS", "Bachelor's Degree"
        DIPLOMA = "DIPLOMA", "Diploma"

    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        OTHER = "OTHER", "Other"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile")

    national_id = models.CharField(max_length=20, unique=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    county = models.CharField(max_length=120, blank=True)
    constituency = models.CharField(max_length=120, blank=True)
    ward = models.CharField(max_length=120, blank=True)
    village = models.CharField(max_length=120, blank=True)
    profile_photo = models.ImageField(upload_to="profiles/", blank=True, null=True)

    institution_type = models.CharField(max_length=20, choices=Institution.InstitutionType.choices, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.SET_NULL, null=True, blank=True)
    course = models.CharField(max_length=255, blank=True)
    qualification = models.CharField(max_length=20, choices=Qualification.choices, blank=True)
    year_of_study = models.PositiveSmallIntegerField(null=True, blank=True)
    admission_number = models.CharField(max_length=100, blank=True, db_index=True)
    expected_graduation_year = models.PositiveSmallIntegerField(null=True, blank=True)
    academic_year = models.CharField(max_length=20, blank=True)

    father_name = models.CharField(max_length=255, blank=True)
    father_occupation = models.CharField(max_length=255, blank=True)
    mother_name = models.CharField(max_length=255, blank=True)
    mother_occupation = models.CharField(max_length=255, blank=True)
    guardian_information = models.TextField(blank=True)
    number_of_dependants = models.PositiveIntegerField(default=0)
    household_income_range = models.CharField(max_length=120, blank=True)
    orphan_status = models.CharField(max_length=50, blank=True)
    disability_information = models.TextField(blank=True)
    financial_circumstances = models.TextField(blank=True)

    completion_percentage = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["admission_number"])]

    def __str__(self):
        return f"{self.user.full_name} Profile"

    def calculate_completion_percentage(self):
        fields = [
            self.national_id,
            self.date_of_birth,
            self.gender,
            self.phone_number,
            self.county,
            self.constituency,
            self.ward,
            self.village,
            self.institution_type,
            self.institution_id,
            self.course,
            self.qualification,
            self.year_of_study,
            self.admission_number,
            self.academic_year,
            self.household_income_range,
        ]
        total_fields = len(fields)
        completed = sum(1 for field in fields if field)
        self.completion_percentage = int((completed / total_fields) * 100) if total_fields else 0
        return self.completion_percentage

    def save(self, *args, **kwargs):
        self.calculate_completion_percentage()
        super().save(*args, **kwargs)
