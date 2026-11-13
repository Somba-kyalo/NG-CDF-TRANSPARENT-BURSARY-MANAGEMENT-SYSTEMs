from django.contrib.auth import views as auth_views
from django.urls import path

from accountsApp import views

app_name = "accounts"

urlpatterns = [
    path("", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_redirect_view, name="dashboard_redirect"),
    path("dashboard/student/", views.student_dashboard_view, name="student_dashboard"),
    path("dashboard/admin/", views.admin_dashboard_view, name="admin_dashboard"),
    path("admin/pending-accounts/", views.pending_accounts_view, name="pending_accounts"),
    path("admin/review-account/<int:user_id>/", views.review_account_view, name="review_account"),
    path("profile/", views.profile_view, name="profile"),
    path("password-reset/", auth_views.PasswordResetView.as_view(template_name="authentication/password_reset_form.html"), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(template_name="authentication/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="authentication/password_reset_confirm.html"), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(template_name="authentication/password_reset_complete.html"), name="password_reset_complete"),
]
