from django import forms
from django.contrib.auth import authenticate

from accountsApp.models import CustomUser, institutional_email_validator
from studentsApp.models import StudentProfile


class StudentRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = ["full_name", "email", "password", "confirm_password"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        institutional_email_validator(email)
        return email

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = CustomUser.Role.STUDENT
        user.account_status = CustomUser.AccountStatus.PENDING
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class EmailLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email", "").lower()
        raw_secret = cleaned_data.get("password")
        if email and raw_secret:
            credentials = {"email": email, "password": raw_secret}
            user = authenticate(**credentials)
            if user is None:
                raise forms.ValidationError("Invalid email or password.")
            cleaned_data["user"] = user
        return cleaned_data


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        exclude = ["user", "completion_percentage", "created_at", "updated_at"]
