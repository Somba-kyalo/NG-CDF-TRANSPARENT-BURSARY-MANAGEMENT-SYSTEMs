from django.contrib.auth.decorators import user_passes_test

from accountsApp.models import CustomUser


ADMIN_PERMISSIONS = {
    "reviewer": [
        "applicationsApp.change_bursaryapplication",
        "applicationsApp.view_bursaryapplication",
        "applicationsApp.add_applicationstatushistory",
    ],
    "allocation_officer": [
        "bursariesApp.add_bursaryaward",
        "bursariesApp.change_bursaryaward",
        "bursariesApp.view_bursarybudget",
    ],
    "auditor": [
        "auditApp.view_auditlog",
        "applicationsApp.view_bursaryapplication",
    ],
}


def is_admin_user(user):
    return user.is_authenticated and user.role == CustomUser.Role.ADMIN


def has_any_permission(user, permission_codes):
    if not is_admin_user(user):
        return False
    if user.is_superuser:
        return True
    return any(user.has_perm(code) for code in permission_codes)


def admin_role_required(role_key):
    permission_codes = ADMIN_PERMISSIONS.get(role_key, [])

    def _check(user):
        if not is_admin_user(user):
            return False
        if user.is_superuser:
            return True
        return any(user.has_perm(code) for code in permission_codes)

    return user_passes_test(_check)
