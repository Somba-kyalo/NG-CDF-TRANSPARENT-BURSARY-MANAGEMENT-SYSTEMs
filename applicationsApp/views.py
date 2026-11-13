import csv
import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Count, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accountsApp.models import CustomUser
from accountsApp.permissions import admin_role_required, is_admin_user
from applicationsApp.forms import (
    AwardAllocationForm,
    ConflictDeclarationForm,
    DOCUMENT_TYPE_MAP,
    StepFiveDeclarationForm,
    StepFourDocumentsForm,
    StepOnePersonalInfoForm,
    StepThreeFinancialForm,
    StepTwoEducationForm,
)
from applicationsApp.models import (
    ApplicationDocument,
    ApplicationStatusHistory,
    BursaryApplication,
    ConflictOfInterest,
)
from applicationsApp.services import log_application_update, log_status_change
from bursariesApp.models import BursaryAward, BursaryBudget


WIZARD_KEY = "bursary_application_wizard"


def _student_required(user):
    return user.is_authenticated and user.role == CustomUser.Role.STUDENT and user.is_approved


def _load_wizard_data(request):
    return request.session.get(WIZARD_KEY, {})


def _save_wizard_data(request, data):
    request.session[WIZARD_KEY] = data
    request.session.modified = True


@login_required
def application_start_view(request: HttpRequest) -> HttpResponse:
    if not _student_required(request.user):
        return redirect("accounts:dashboard_redirect")

    profile = getattr(request.user, "student_profile", None)
    initial = {
        "full_name": request.user.full_name,
        "email": request.user.email,
        "phone_number": getattr(profile, "phone_number", ""),
        "national_id": getattr(profile, "national_id", ""),
    }

    if request.method == "POST":
        form = StepOnePersonalInfoForm(request.POST, initial=initial)
        if form.is_valid():
            wizard = _load_wizard_data(request)
            wizard["step1"] = {
                "phone_number": form.cleaned_data.get("phone_number", ""),
                "national_id": form.cleaned_data.get("national_id", ""),
            }
            _save_wizard_data(request, wizard)
            return redirect("applications:step2")
    else:
        form = StepOnePersonalInfoForm(initial=initial)

    return render(request, "student/application_step1.html", {"form": form, "step": 1})


@login_required
def application_step2_view(request: HttpRequest) -> HttpResponse:
    if not _student_required(request.user):
        return redirect("accounts:dashboard_redirect")

    wizard = _load_wizard_data(request)
    initial = wizard.get("step2", {})

    if request.method == "POST":
        form = StepTwoEducationForm(request.POST)
        if form.is_valid():
            wizard["step2"] = {
                "institution_id": form.cleaned_data["institution"].id,
                "course": form.cleaned_data["course"],
                "qualification": form.cleaned_data["qualification"],
                "year_of_study": form.cleaned_data["year_of_study"],
                "admission_number": form.cleaned_data["admission_number"],
                "academic_year": form.cleaned_data["academic_year"],
                "institution_location": form.cleaned_data["institution_location"],
            }
            _save_wizard_data(request, wizard)
            return redirect("applications:step3")
    else:
        if "institution_id" in initial:
            initial = {**initial, "institution": initial["institution_id"]}
        form = StepTwoEducationForm(initial=initial)

    return render(request, "student/application_step2.html", {"form": form, "step": 2})


@login_required
def application_step3_view(request: HttpRequest) -> HttpResponse:
    if not _student_required(request.user):
        return redirect("accounts:dashboard_redirect")

    wizard = _load_wizard_data(request)

    if request.method == "POST":
        form = StepThreeFinancialForm(request.POST)
        if form.is_valid():
            wizard["step3"] = {
                key: (str(value) if isinstance(value, Decimal) else value)
                for key, value in form.cleaned_data.items()
            }
            _save_wizard_data(request, wizard)
            return redirect("applications:step4")
    else:
        form = StepThreeFinancialForm(initial=wizard.get("step3", {}))

    return render(request, "student/application_step3.html", {"form": form, "step": 3})


@login_required
def application_step4_view(request: HttpRequest) -> HttpResponse:
    if not _student_required(request.user):
        return redirect("accounts:dashboard_redirect")

    if request.method == "POST":
        form = StepFourDocumentsForm(request.POST, request.FILES)
        if form.is_valid():
            request.session["application_step4_files"] = {
                key: request.FILES[key].name
                for key in request.FILES
                if key in DOCUMENT_TYPE_MAP
            }
            request.session.modified = True
            return redirect("applications:step5")
    else:
        form = StepFourDocumentsForm()

    return render(request, "student/application_step4.html", {"form": form, "step": 4})


@login_required
def application_step5_view(request: HttpRequest) -> HttpResponse:
    if not _student_required(request.user):
        return redirect("accounts:dashboard_redirect")

    if request.method == "POST":
        form = StepFiveDeclarationForm(request.POST)
        if form.is_valid():
            wizard = _load_wizard_data(request)
            wizard["step5"] = {"declaration_accepted": form.cleaned_data["declaration_accepted"]}
            _save_wizard_data(request, wizard)
            return redirect("applications:step6")
    else:
        form = StepFiveDeclarationForm()

    return render(request, "student/application_step5.html", {"form": form, "step": 5})


@login_required
def application_step6_submit_view(request: HttpRequest) -> HttpResponse:
    if not _student_required(request.user):
        return redirect("accounts:dashboard_redirect")

    wizard = _load_wizard_data(request)
    required = ["step2", "step3", "step5"]
    if any(step not in wizard for step in required):
        messages.error(request, "Complete all required steps before submitting.")
        return redirect("applications:step1")

    if request.method == "POST":
        step2 = wizard["step2"]
        step3 = wizard["step3"]

        if not wizard.get("step5", {}).get("declaration_accepted"):
            messages.error(request, "Declaration is required.")
            return redirect("applications:step5")

        try:
            application = BursaryApplication.objects.create(
                student=request.user,
                student_profile=getattr(request.user, "student_profile", None),
                institution_id=step2["institution_id"],
                course=step2["course"],
                qualification=step2["qualification"],
                year_of_study=step2["year_of_study"],
                admission_number=step2["admission_number"],
                academic_year=step2["academic_year"],
                institution_location=step2["institution_location"],
                annual_household_income=Decimal(step3["annual_household_income"]),
                number_of_dependants=step3["number_of_dependants"],
                other_sources_of_financial_support=step3.get("other_sources_of_financial_support", ""),
                previous_bursary_awards=step3.get("previous_bursary_awards", ""),
                amount_requested=Decimal(step3["amount_requested"]),
                financial_need_explanation=step3["financial_need_explanation"],
                declaration_accepted=True,
                status=BursaryApplication.Status.SUBMITTED,
                submitted_at=timezone.now(),
            )
        except IntegrityError:
            messages.error(request, "Duplicate application detected for the same academic year.")
            return redirect("applications:list")

        for field_name, doc_type in DOCUMENT_TYPE_MAP.items():
            uploaded = request.FILES.get(field_name)
            if uploaded:
                ApplicationDocument.objects.create(
                    application=application,
                    document_type=doc_type,
                    file=uploaded,
                )

        log_status_change(
            application=application,
            previous_status=BursaryApplication.Status.DRAFT,
            new_status=BursaryApplication.Status.SUBMITTED,
            changed_by=request.user,
            remarks="Application submitted by student",
        )

        request.session.pop(WIZARD_KEY, None)
        request.session.pop("application_step4_files", None)
        messages.success(request, f"Application submitted. Reference: {application.reference_number}")
        return redirect("applications:detail", application_id=application.id)

    preview = {
        "step2": wizard.get("step2", {}),
        "step3": wizard.get("step3", {}),
        "files": request.session.get("application_step4_files", {}),
    }
    return render(request, "student/application_step6_submit.html", {"preview": preview, "step": 6})


@login_required
def application_list_view(request: HttpRequest) -> HttpResponse:
    if request.user.role != CustomUser.Role.STUDENT:
        return redirect("accounts:dashboard_redirect")

    applications = BursaryApplication.objects.filter(student=request.user).select_related("institution")
    status = request.GET.get("status", "")
    if status:
        applications = applications.filter(status=status)

    return render(
        request,
        "student/applications_list.html",
        {
            "applications": applications.order_by("-created_at"),
            "status": status,
            "statuses": BursaryApplication.Status.choices,
        },
    )


@login_required
def application_detail_view(request: HttpRequest, application_id: int) -> HttpResponse:
    application = get_object_or_404(BursaryApplication.objects.select_related("institution", "student"), id=application_id)
    if request.user.role == CustomUser.Role.STUDENT and application.student_id != request.user.id:
        return redirect("applications:list")

    timeline = ApplicationStatusHistory.objects.filter(application=application).select_related("changed_by")
    documents = ApplicationDocument.objects.filter(application=application)
    return render(
        request,
        "student/application_detail.html",
        {"application": application, "timeline": timeline, "documents": documents},
    )


@login_required
@admin_role_required("reviewer")
def admin_application_queue_view(request: HttpRequest) -> HttpResponse:
    applications = BursaryApplication.objects.select_related("student", "institution")
    status = request.GET.get("status", "")
    if status:
        applications = applications.filter(status=status)

    return render(
        request,
        "admin/applications_queue.html",
        {
            "applications": applications.order_by("-created_at")[:100],
            "status": status,
            "statuses": BursaryApplication.Status.choices,
        },
    )


@login_required
@admin_role_required("reviewer")
def admin_application_detail_view(request: HttpRequest, application_id: int) -> HttpResponse:
    application = get_object_or_404(BursaryApplication.objects.select_related("student", "institution"), id=application_id)
    timeline = application.status_history.select_related("changed_by")
    documents = application.documents.all()
    conflict_form = ConflictDeclarationForm()
    award_form = AwardAllocationForm()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update_status":
            new_status = request.POST.get("new_status")
            remarks = request.POST.get("remarks", "")
            previous = application.status
            if new_status in BursaryApplication.Status.values:
                application.status = new_status
                application.save(update_fields=["status", "updated_at"])
                log_status_change(application, previous, new_status, request.user, remarks)
                messages.success(request, "Application status updated.")
                return redirect("applications:admin_detail", application_id=application.id)

        if action == "declare_conflict":
            conflict_form = ConflictDeclarationForm(request.POST)
            if conflict_form.is_valid():
                ConflictOfInterest.objects.get_or_create(
                    application=application,
                    administrator=request.user,
                    defaults={"reason": conflict_form.cleaned_data["reason"]},
                )
                messages.warning(request, "Conflict of interest declared.")
                return redirect("applications:admin_detail", application_id=application.id)

        if action == "allocate_award":
            if ConflictOfInterest.objects.filter(application=application, administrator=request.user).exists():
                messages.error(request, "You cannot allocate award due to declared conflict of interest.")
                return redirect("applications:admin_detail", application_id=application.id)

            award_form = AwardAllocationForm(request.POST)
            if award_form.is_valid():
                budget = award_form.cleaned_data["budget"]
                amount_approved = award_form.cleaned_data["amount_approved"]
                if amount_approved > budget.remaining_balance:
                    messages.error(request, "Allocation exceeds available budget balance.")
                    return redirect("applications:admin_detail", application_id=application.id)

                previous_allocated = budget.allocated_amount
                award, created = BursaryAward.objects.get_or_create(
                    application=application,
                    defaults={
                        "amount_requested": application.amount_requested,
                        "amount_approved": amount_approved,
                        "assessment_score": award_form.cleaned_data["assessment_score"],
                        "approved_by": request.user,
                        "reason_for_allocation": award_form.cleaned_data["reason_for_allocation"],
                        "budget": budget,
                    },
                )
                if not created:
                    old = award.amount_approved
                    budget.allocated_amount = budget.allocated_amount - old + amount_approved
                    award.amount_approved = amount_approved
                    award.assessment_score = award_form.cleaned_data["assessment_score"]
                    award.reason_for_allocation = award_form.cleaned_data["reason_for_allocation"]
                    award.approved_by = request.user
                    award.budget = budget
                    award.full_clean()
                    award.save()
                else:
                    budget.allocated_amount = budget.allocated_amount + amount_approved
                    award.full_clean()
                    award.save()

                budget.save(update_fields=["allocated_amount", "updated_at"])

                prev_status = application.status
                application.status = (
                    BursaryApplication.Status.PARTIALLY_AWARDED
                    if amount_approved < application.amount_requested
                    else BursaryApplication.Status.APPROVED
                )
                application.save(update_fields=["status", "updated_at"])
                log_status_change(
                    application,
                    prev_status,
                    application.status,
                    request.user,
                    f"Award allocation updated from {previous_allocated} to {budget.allocated_amount}",
                )
                log_application_update(
                    application,
                    actor=request.user,
                    previous_values={"allocated_amount": str(previous_allocated)},
                    new_values={"allocated_amount": str(budget.allocated_amount)},
                    reason="Bursary allocation",
                )
                messages.success(request, "Award allocation saved.")
                return redirect("applications:admin_detail", application_id=application.id)

    return render(
        request,
        "admin/application_detail.html",
        {
            "application": application,
            "timeline": timeline,
            "documents": documents,
            "conflict_form": conflict_form,
            "award_form": award_form,
            "conflicts": ConflictOfInterest.objects.filter(application=application).select_related("administrator"),
            "has_award": hasattr(application, "award"),
        },
    )


@login_required
@admin_role_required("auditor")
def admin_analytics_view(request: HttpRequest) -> HttpResponse:
    per_year = list(
        BursaryApplication.objects.values("academic_year").annotate(count=Count("id")).order_by("academic_year")
    )
    per_institution = list(
        BursaryApplication.objects.values("institution__name").annotate(count=Count("id")).order_by("-count")[:10]
    )
    per_ward = list(BursaryApplication.objects.values("student__student_profile__ward").annotate(count=Count("id")).order_by("-count")[:10])
    status_counts = list(BursaryApplication.objects.values("status").annotate(count=Count("id")))

    budgets = BursaryBudget.objects.all().order_by("academic_year")
    budget_labels = [b.academic_year for b in budgets]
    budget_total = [float(b.total_budget) for b in budgets]
    budget_allocated = [float(b.allocated_amount) for b in budgets]

    context = {
        "chart_data": {
            "per_year_labels": [row["academic_year"] for row in per_year],
            "per_year_values": [row["count"] for row in per_year],
            "institution_labels": [row["institution__name"] or "Unknown" for row in per_institution],
            "institution_values": [row["count"] for row in per_institution],
            "ward_labels": [row["student__student_profile__ward"] or "Unknown" for row in per_ward],
            "ward_values": [row["count"] for row in per_ward],
            "status_labels": [row["status"] for row in status_counts],
            "status_values": [row["count"] for row in status_counts],
            "budget_labels": budget_labels,
            "budget_total": budget_total,
            "budget_allocated": budget_allocated,
        },
        "total_allocated": budgets.aggregate(v=Sum("allocated_amount"))["v"] or 0,
        "total_budget": budgets.aggregate(v=Sum("total_budget"))["v"] or 0,
    }
    return render(request, "admin/analytics.html", context)


@login_required
@admin_role_required("auditor")
def export_applications_csv_view(request: HttpRequest) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="applications_report.csv"'

    writer = csv.writer(response)
    writer.writerow(["Reference", "Student", "Academic Year", "Institution", "Status", "Amount Requested", "Submitted At"])

    rows = BursaryApplication.objects.select_related("student", "institution").order_by("-created_at")
    for row in rows:
        writer.writerow(
            [
                row.reference_number,
                row.student.full_name,
                row.academic_year,
                row.institution.name,
                row.status,
                row.amount_requested,
                row.submitted_at,
            ]
        )

    return response


@login_required
@admin_role_required("auditor")
def export_financial_csv_view(request: HttpRequest) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="financial_report.csv"'

    writer = csv.writer(response)
    writer.writerow(["Academic Year", "Total Budget", "Allocated", "Disbursed", "Remaining"])

    for budget in BursaryBudget.objects.order_by("academic_year"):
        writer.writerow([
            budget.academic_year,
            budget.total_budget,
            budget.allocated_amount,
            budget.disbursed_amount,
            budget.remaining_balance,
        ])

    return response
