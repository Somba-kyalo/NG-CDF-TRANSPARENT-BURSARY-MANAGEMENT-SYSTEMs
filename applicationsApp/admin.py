from django.contrib import admin

from applicationsApp.models import (
    Appeal,
    ApplicationAssessment,
    ApplicationDocument,
    ApplicationStatusHistory,
    BursaryApplication,
    ConflictOfInterest,
)

admin.site.register(BursaryApplication)
admin.site.register(ApplicationDocument)
admin.site.register(ApplicationStatusHistory)
admin.site.register(ApplicationAssessment)
admin.site.register(Appeal)
admin.site.register(ConflictOfInterest)
