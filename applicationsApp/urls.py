from django.urls import path

from applicationsApp import views

app_name = "applications"

urlpatterns = [
    path("apply/step-1/", views.application_start_view, name="step1"),
    path("apply/step-2/", views.application_step2_view, name="step2"),
    path("apply/step-3/", views.application_step3_view, name="step3"),
    path("apply/step-4/", views.application_step4_view, name="step4"),
    path("apply/step-5/", views.application_step5_view, name="step5"),
    path("apply/step-6/", views.application_step6_submit_view, name="step6"),
    path("my-applications/", views.application_list_view, name="list"),
    path("my-applications/<int:application_id>/", views.application_detail_view, name="detail"),
    path("admin/applications/", views.admin_application_queue_view, name="admin_queue"),
    path("admin/applications/<int:application_id>/", views.admin_application_detail_view, name="admin_detail"),
    path("admin/analytics/", views.admin_analytics_view, name="analytics"),
    path("admin/export/applications.csv", views.export_applications_csv_view, name="export_applications_csv"),
    path("admin/export/financial.csv", views.export_financial_csv_view, name="export_financial_csv"),
]
