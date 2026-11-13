from auditApp.models import AuditLog
from applicationsApp.models import ApplicationStatusHistory, BursaryApplication


def log_status_change(application, previous_status, new_status, changed_by, remarks=""):
    if previous_status == new_status:
        return

    ApplicationStatusHistory.objects.create(
        application=application,
        previous_status=previous_status,
        new_status=new_status,
        changed_by=changed_by,
        remarks=remarks,
    )

    AuditLog.objects.create(
        actor=changed_by,
        model_name="BursaryApplication",
        object_id=str(application.id),
        action="status_change",
        previous_values={"status": previous_status},
        new_values={"status": new_status},
        reason=remarks,
    )


def log_application_update(application, actor, previous_values, new_values, reason=""):
    AuditLog.objects.create(
        actor=actor,
        model_name="BursaryApplication",
        object_id=str(application.id),
        action="update",
        previous_values=previous_values,
        new_values=new_values,
        reason=reason,
    )
