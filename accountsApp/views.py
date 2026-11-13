from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accountsApp.forms import EmailLoginForm, StudentProfileForm, StudentRegistrationForm
from accountsApp.models import AccountApproval, CustomUser
from announcementsApp.models import Announcement
from applicationsApp.models import BursaryApplication
from bursariesApp.models import ApplicationPeriod, BursaryBudget
from notificationsApp.models import Notification


def is_admin(user):
    return user.is_authenticated and user.role == CustomUser.Role.ADMIN


def register_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("accounts:dashboard_redirect")

    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            AccountApproval.objects.get_or_create(user=user)
            Notification.objects.create(
                user=user,
                title="Account submitted",
                message="Your student account is pending administrator approval.",
            )
            messages.success(request, "Registration successful. Await account approval before login.")
            return redirect("accounts:login")
    else:
        form = StudentRegistrationForm()

    return render(request, "authentication/register.html", {"form": form})


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("accounts:dashboard_redirect")

    if request.method == "POST":
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data["user"]
            if user.role == CustomUser.Role.STUDENT and not user.is_approved:
                if user.account_status == CustomUser.AccountStatus.REJECTED:
                    reason = ""
                    approval = AccountApproval.objects.filter(user=user).first()
                    if approval and approval.rejection_reason:
                        reason = f" Reason: {approval.rejection_reason}"
                    messages.error(request, f"Your account has been rejected.{reason}")
                else:
                    messages.warning(request, "Your account is pending administrator approval.")
                return redirect("accounts:login")

            login(request, user)
            messages.success(request, "Login successful.")
            return redirect("accounts:dashboard_redirect")
    else:
        form = EmailLoginForm()

    return render(request, "authentication/login.html", {"form": form})


@login_required
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("accounts:login")


@login_required
def dashboard_redirect_view(request: HttpRequest) -> HttpResponse:
    if request.user.role == CustomUser.Role.ADMIN:
        return redirect("accounts:admin_dashboard")

    if not request.user.is_approved:
        messages.warning(request, "Your account is pending approval.")
        logout(request)
        return redirect("accounts:login")

    return redirect("accounts:student_dashboard")


@login_required
def student_dashboard_view(request: HttpRequest) -> HttpResponse:
    if request.user.role != CustomUser.Role.STUDENT:
        return redirect("accounts:dashboard_redirect")

    if not request.user.is_approved:
        messages.warning(request, "Account pending approval.")
        return redirect("accounts:login")

    applications = BursaryApplication.objects.filter(student=request.user)
    recent_applications = applications.order_by("-created_at")[:5]
    announcements = Announcement.objects.filter(is_active=True)[:5]
    important_dates = ApplicationPeriod.objects.filter(is_active=True).order_by("opens_on")[:5]

    context = {
        "total_applications": applications.count(),
        "pending_applications": applications.filter(status__in=["SUBMITTED", "UNDER_REVIEW", "VERIFICATION_REQUIRED"]).count(),
        "approved_applications": applications.filter(status="APPROVED").count(),
        "rejected_applications": applications.filter(status="REJECTED").count(),
        "awarded_total": sum(float(app.award.amount_approved) for app in applications.select_related("award") if hasattr(app, "award")),
        "recent_applications": recent_applications,
        "announcements": announcements,
        "important_dates": important_dates,
    }
    return render(request, "student/dashboard.html", context)


@login_required
@user_passes_test(is_admin)
def admin_dashboard_view(request: HttpRequest) -> HttpResponse:
    students = CustomUser.objects.filter(role=CustomUser.Role.STUDENT)
    applications = BursaryApplication.objects.all()
    budgets = BursaryBudget.objects.all()
    context = {
        "total_students": students.count(),
        "pending_accounts": students.filter(account_status=CustomUser.AccountStatus.PENDING).count(),
        "approved_accounts": students.filter(account_status=CustomUser.AccountStatus.APPROVED).count(),
        "rejected_accounts": students.filter(account_status=CustomUser.AccountStatus.REJECTED).count(),
        "total_applications": applications.count(),
        "pending_applications": applications.filter(status__in=["SUBMITTED", "UNDER_REVIEW"]).count(),
        "approved_applications": applications.filter(status="APPROVED").count(),
        "rejected_applications": applications.filter(status="REJECTED").count(),
        "total_budget": sum(float(b.total_budget) for b in budgets),
        "allocated_budget": sum(float(b.allocated_amount) for b in budgets),
        "remaining_budget": sum(float(b.remaining_balance) for b in budgets),
    }
    return render(request, "admin/dashboard.html", context)


@login_required
@user_passes_test(is_admin)
def pending_accounts_view(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "")
    approvals = AccountApproval.objects.filter(status=CustomUser.AccountStatus.PENDING).select_related("user")
    if query:
        approvals = approvals.filter(Q(user__full_name__icontains=query) | Q(user__email__icontains=query))

    paginator = Paginator(approvals, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "admin/pending_accounts.html", {"page": page, "query": query})


@login_required
@user_passes_test(is_admin)
def review_account_view(request: HttpRequest, user_id: int) -> HttpResponse:
    approval = get_object_or_404(AccountApproval.objects.select_related("user"), user_id=user_id)
    action = request.POST.get("action")
    reason = request.POST.get("reason", "").strip()

    if request.method != "POST":
        return redirect("accounts:pending_accounts")

    if action == "approve":
        approval.approve(request.user)
        Notification.objects.create(
            user=approval.user,
            title="Account approved",
            message="Your account has been approved. You can now log in.",
        )
        messages.success(request, f"{approval.user.full_name} approved.")
    elif action == "reject":
        if not reason:
            messages.error(request, "Rejection reason is required.")
            return redirect("accounts:pending_accounts")

        approval.reject(request.user, reason)
        Notification.objects.create(
            user=approval.user,
            title="Account rejected",
            message=f"Your account registration was rejected. Reason: {reason}",
        )
        messages.warning(request, f"{approval.user.full_name} rejected.")
    else:
        messages.error(request, "Invalid review action.")

    approval.reviewed_at = timezone.now()
    approval.save(update_fields=["reviewed_at", "updated_at"])
    return redirect("accounts:pending_accounts")


@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    if request.user.role != CustomUser.Role.STUDENT:
        return redirect("accounts:dashboard_redirect")

    profile = getattr(request.user, "student_profile", None)
    if profile is None:
        from studentsApp.models import StudentProfile

        profile = StudentProfile.objects.create(user=request.user)

    if request.method == "POST":
        form = StudentProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile")
    else:
        form = StudentProfileForm(instance=profile)

    return render(request, "student/profile.html", {"form": form, "profile": profile})
