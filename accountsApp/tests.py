from django.test import TestCase
from django.urls import reverse

from accountsApp.models import AccountApproval, CustomUser


class RegistrationValidationTests(TestCase):
    def test_rejects_non_institutional_email(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "full_name": "Student One",
                "email": "student@gmail.com",
                "password": "StrongPass123!",
                "confirm_password": "StrongPass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ".ac.ke")
        self.assertEqual(CustomUser.objects.count(), 0)

    def test_registration_creates_pending_student(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "full_name": "Student One",
                "email": "student@ttu.ac.ke",
                "password": "StrongPass123!",
                "confirm_password": "StrongPass123!",
            },
        )
        self.assertRedirects(response, reverse("accounts:login"))
        user = CustomUser.objects.get(email="student@ttu.ac.ke")
        self.assertEqual(user.role, CustomUser.Role.STUDENT)
        self.assertEqual(user.account_status, CustomUser.AccountStatus.PENDING)
        self.assertTrue(AccountApproval.objects.filter(user=user, status=CustomUser.AccountStatus.PENDING).exists())


class AccountApprovalWorkflowTests(TestCase):
    def setUp(self):
        self.student = CustomUser.objects.create_user(
            email="student@jkuat.ac.ke",
            full_name="Pending Student",
            raw_password="StrongPass123!",
            role=CustomUser.Role.STUDENT,
            account_status=CustomUser.AccountStatus.PENDING,
        )
        self.admin_user = CustomUser.objects.create_superuser(
            email="admin@ngcdf.go.ke",
            full_name="Admin User",
            raw_password="AdminPass123!",
        )

    def test_pending_student_cannot_login(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"email": self.student.email, "password": "StrongPass123!"},
            follow=True,
        )
        self.assertContains(response, "pending administrator approval")

    def test_admin_can_approve_student_and_student_can_login(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("accounts:review_account", args=[self.student.id]),
            {"action": "approve"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.student.refresh_from_db()
        self.assertEqual(self.student.account_status, CustomUser.AccountStatus.APPROVED)

        self.client.logout()
        login_response = self.client.post(
            reverse("accounts:login"),
            {"email": self.student.email, "password": "StrongPass123!"},
            follow=True,
        )
        self.assertRedirects(login_response, reverse("accounts:student_dashboard"))

    def test_admin_dashboard_access_requires_admin_role(self):
        self.student.account_status = CustomUser.AccountStatus.APPROVED
        self.student.save(update_fields=["account_status"])
        self.client.force_login(self.student)

        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertEqual(response.status_code, 302)
