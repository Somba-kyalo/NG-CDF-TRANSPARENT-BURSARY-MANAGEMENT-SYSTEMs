from decimal import Decimal

from django import forms

from applicationsApp.models import (
    ApplicationDocument,
    BursaryApplication,
    ConflictOfInterest,
)
from bursariesApp.models import BursaryBudget
from studentsApp.models import Institution


class StepOnePersonalInfoForm(forms.Form):
    full_name = forms.CharField(disabled=True, required=False)
    email = forms.EmailField(disabled=True, required=False)
    phone_number = forms.CharField(required=False, max_length=20)
    national_id = forms.CharField(required=False, max_length=20)


class StepTwoEducationForm(forms.Form):
    institution = forms.ModelChoiceField(queryset=Institution.objects.all())
    course = forms.CharField(max_length=255)
    qualification = forms.ChoiceField(choices=[("BACHELORS", "Bachelor's Degree"), ("DIPLOMA", "Diploma")])
    year_of_study = forms.IntegerField(min_value=1, max_value=8)
    admission_number = forms.CharField(max_length=100)
    academic_year = forms.CharField(max_length=20)
    institution_location = forms.CharField(max_length=255)


class StepThreeFinancialForm(forms.Form):
    annual_household_income = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    number_of_dependants = forms.IntegerField(min_value=0)
    other_sources_of_financial_support = forms.CharField(required=False, widget=forms.Textarea)
    previous_bursary_awards = forms.CharField(required=False, widget=forms.Textarea)
    amount_requested = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    financial_need_explanation = forms.CharField(widget=forms.Textarea)


class StepFourDocumentsForm(forms.Form):
    national_id_copy = forms.FileField(required=False)
    admission_letter = forms.FileField(required=False)
    fee_structure = forms.FileField(required=False)
    fee_statement = forms.FileField(required=False)
    transcript = forms.FileField(required=False)
    guardian_id = forms.FileField(required=False)
    death_certificate = forms.FileField(required=False)
    other_document = forms.FileField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        max_size = 5 * 1024 * 1024
        for _, uploaded in cleaned_data.items():
            if uploaded and uploaded.size > max_size:
                raise forms.ValidationError("Each file must be 5MB or less.")
        return cleaned_data


class StepFiveDeclarationForm(forms.Form):
    declaration_accepted = forms.BooleanField()


class ApplicationStatusUpdateForm(forms.Form):
    new_status = forms.ChoiceField(choices=BursaryApplication.Status.choices)
    remarks = forms.CharField(widget=forms.Textarea, required=False)


class ConflictDeclarationForm(forms.ModelForm):
    class Meta:
        model = ConflictOfInterest
        fields = ["reason"]


class AwardAllocationForm(forms.Form):
    budget = forms.ModelChoiceField(queryset=BursaryBudget.objects.all())
    amount_approved = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    assessment_score = forms.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal("0"))
    reason_for_allocation = forms.CharField(widget=forms.Textarea)


DOCUMENT_TYPE_MAP = {
    "national_id_copy": ApplicationDocument.DocumentType.NATIONAL_ID,
    "admission_letter": ApplicationDocument.DocumentType.ADMISSION_LETTER,
    "fee_structure": ApplicationDocument.DocumentType.FEE_STRUCTURE,
    "fee_statement": ApplicationDocument.DocumentType.FEE_STATEMENT,
    "transcript": ApplicationDocument.DocumentType.TRANSCRIPT,
    "guardian_id": ApplicationDocument.DocumentType.GUARDIAN_ID,
    "death_certificate": ApplicationDocument.DocumentType.DEATH_CERTIFICATE,
    "other_document": ApplicationDocument.DocumentType.OTHER,
}
