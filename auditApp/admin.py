from django.contrib import admin

from auditApp.models import AuditLog

admin.site.register(AuditLog)
