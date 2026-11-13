from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accountsApp.models import CustomUser
from applicationsApp.models import BursaryApplication
from bursariesApp.models import BursaryBudget
from studentsApp.models import Institution


class MultiStepApplicationWorkflowTests(TestCase):
    def setUp(self):
        self.student = CustomUser.objects.create_user(
            email="student@uon.ac.ke",
            full_name="Workflow Student",
            raw_password="StrongPass123!",
            role=CustomUser.Role.STUDENT,
            account_status=CustomUser.AccountStatus.APPROVED,
        )
        self.institution = Institution.objects.create(
            name="University of Nairobi",
            institution_type=Institution.InstitutionType.UNIVERSITY,
        )
        self.client.force_login(self.student)

    def _complete_minimal_wizard(self, academic_year="2026/2027"):
        self.client.post(reverse("applications:step1"), {"phone_number": "0712345678", "national_id": "12345678"})
        self.client.post(
            reverse("applications:step2"),
            {
                "institution": self.institution.id,
                "course": "Computer Science",
                "qualification": "BACHELORS",
                "year_of_study": 2,
                "admission_number": "UON1234",
                "academic_year": academic_year,
                "institution_location": "Nairobi",
            },
        )
        self.client.post(
            reverse("applications:step3"),
            {
                "annual_household_income": "120000",
                "number_of_dependants": 4,
                "other_sources_of_financial_support": "None",
                "previous_bursary_awards": "None",
                "amount_requested": "50000",
                "financial_need_explanation": "Need support",
            },
        )
        self.client.post(reverse("applications:step5"), {"declaration_accepted": True})

    def test_multistep_submission_creates_submitted_application(self):
        self._complete_minimal_wizard()
        response = self.client.post(reverse("applications:step6"), follow=True)

        self.assertEqual(response.status_code, 200)
        app = BursaryApplication.objects.get(student=self.student, academic_year="2026/2027")
        self.assertEqual(app.status, BursaryApplication.Status.SUBMITTED)
        self.assertTrue(app.reference_number.startswith("NGCDF-"))

    def test_duplicate_application_same_year_is_blocked(self):
        BursaryApplication.objects.create(
            student=self.student,
            student_profile=self.student.student_profile,
            institution=self.institution,
            course="Computer Science",
            qualification="BACHELORS",
            year_of_study=2,
            admission_number="UON1234",
            academic_year="2026/2027",
            institution_location="Nairobi",
            annual_household_income=Decimal("120000.00"),
            number_of_dependants=4,
            amount_requested=Decimal("50000.00"),
            financial_need_explanation="Need support",
            declaration_accepted=True,
        )

        self._complete_minimal_wizard(academic_year="2026/2027")
        response = self.client.post(reverse("applications:step6"), follow=True)

        self.assertContains(response, "Duplicate application detected")
        self.assertEqual(BursaryApplication.objects.filter(student=self.student, academic_year="2026/2027").count(), 1)


class AdminAllocationAndExportTests(TestCase):
    def setUp(self):
        self.student = CustomUser.objects.create_user(
            email="student2@ttu.ac.ke",
            full_name="Student Two",
            raw_password="StrongPass123!",
            role=CustomUser.Role.STUDENT,
            account_status=CustomUser.AccountStatus.APPROVED,
        )
        self.admin = CustomUser.objects.create_superuser(
            email="admin2@ngcdf.go.ke",
            full_name="Admin Two",
            raw_password="AdminPass123!",
        )
        self.institution = Institution.objects.create(
            name="Technical University of Mombasa",
            institution_type=Institution.InstitutionType.UNIVERSITY,
        )
        self.application = BursaryApplication.objects.create(
            student=self.student,
            student_profile=self.student.student_profile,
            institution=self.institution,
            course="Engineering",
            qualification="BACHELORS",
            year_of_study=3,
            admission_number="TUM100",
            academic_year="2027/2028",
            institution_location="Mombasa",
            annual_household_income=Decimal("90000.00"),
            number_of_dependants=5,
            amount_requested=Decimal("80000.00"),
            financial_need_explanation="Support needed",
            declaration_accepted=True,
            status=BursaryApplication.Status.VERIFIED,
        )
        self.budget = BursaryBudget.objects.create(
            academic_year="2027/2028",
            total_budget=Decimal("100000.00"),
            allocated_amount=Decimal("95000.00"),
            disbursed_amount=Decimal("0.00"),
            created_by=self.admin,
        )

    def test_allocation_cannot_exceed_remaining_budget(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("applications:admin_detail", args=[self.application.id]),
            {
                "action": "allocate_award",
                "budget": self.budget.id,
                "amount_approved": "10000",
                "assessment_score": "78",
                "reason_for_allocation": "Merit",
            },
            follow=True,
        )
        self.assertContains(response, "exceeds available budget")

    def test_export_requires_admin_access(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("applications:export_applications_csv"))
        self.assertEqual(response.status_code, 302)

    def test_admin_can_export_csv(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("applications:export_applications_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("Reference,Student,Academic Year", response.content.decode())
