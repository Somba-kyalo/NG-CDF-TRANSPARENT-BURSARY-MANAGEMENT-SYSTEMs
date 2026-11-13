from django.conf import settings
from django.db import models


class SupportRequest(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        PHONE = "PHONE", "Phone"
        WHATSAPP = "WHATSAPP", "WhatsApp"
        FACEBOOK = "FACEBOOK", "Facebook"
        INSTAGRAM = "INSTAGRAM", "Instagram"
        X = "X", "X (Twitter)"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_requests")
    subject = models.CharField(max_length=255)
    message = models.TextField()
    preferred_channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.EMAIL)
    status = models.CharField(
        max_length=20,
        choices=[("OPEN", "Open"), ("IN_PROGRESS", "In Progress"), ("RESOLVED", "Resolved")],
        default="OPEN",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.subject
