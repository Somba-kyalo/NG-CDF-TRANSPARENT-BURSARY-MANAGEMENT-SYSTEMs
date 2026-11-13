# NG-CDF STUDENT PORTAL – Transparent Constituency Bursary Management System

## Proposed Architecture (Implemented Foundation)

- **Django project config**: `config/`
- **Core domain apps**:
  - `accountsApp` (custom user, authentication, account approval)
  - `studentsApp` (institutions, student profile)
  - `applicationsApp` (application lifecycle, documents, status history, appeals, conflicts)
  - `bursariesApp` (opportunities, periods, criteria, budgets, awards)
  - `announcementsApp`, `notificationsApp`, `auditApp`, `supportApp`, `analyticsApp`
- **Shared UI**:
  - `templates/base.html`
  - `templates/authentication/`
  - `templates/student/`
  - `templates/admin/`
  - `static/css/main.css`

## Implemented Phase

1. Custom `CustomUser` model with email login and role separation (`STUDENT`, `ADMIN`).
2. Institutional email validation for student registration (`*.ac.ke`) on backend.
3. Student registration with **pending approval workflow**.
4. Admin review flow for approving/rejecting student accounts with rejection reason.
5. Role-aware dashboard routing and protected student/admin dashboards.
6. Core transparency models added for applications, status history, eligibility, awards, budget, appeals, conflicts, notifications and audit logs.
7. Password reset routes wired using Django auth views.
8. Focused tests for registration validation and account approval/login gating.

## Run locally

```bash
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Validation

```bash
python manage.py check
python manage.py test
```
