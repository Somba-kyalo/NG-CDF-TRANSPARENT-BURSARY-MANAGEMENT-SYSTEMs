from django.db.models.signals import post_save
from django.dispatch import receiver

from accountsApp.models import AccountApproval, CustomUser
from studentsApp.models import StudentProfile


@receiver(post_save, sender=CustomUser)
def create_student_related_records(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.role == CustomUser.Role.STUDENT:
        AccountApproval.objects.get_or_create(user=instance)
        StudentProfile.objects.get_or_create(user=instance)
