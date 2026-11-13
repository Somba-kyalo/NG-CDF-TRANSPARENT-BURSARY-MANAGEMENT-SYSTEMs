from django.contrib import admin

from bursariesApp.models import ApplicationPeriod, BursaryAward, BursaryBudget, BursaryOpportunity, EligibilityCriteria

admin.site.register(ApplicationPeriod)
admin.site.register(BursaryOpportunity)
admin.site.register(EligibilityCriteria)
admin.site.register(BursaryBudget)
admin.site.register(BursaryAward)
