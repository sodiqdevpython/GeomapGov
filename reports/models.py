from django.db import models
from django.conf import settings
from utils.models import BaseModel
from .choices import ReportStatus, AttachmentType


def report_upload_path(instance, filename: str) -> str:
    # media/reports/<report_id>/<filename>
    return f"reports/{instance.report_id}/{filename}"


class Report(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports")
    description = models.TextField()

    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    status = models.CharField(max_length=16, choices=ReportStatus.choices, default=ReportStatus.NEW)

    # Keyin operator/boss qo'shsak:
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_reports",
    )

    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user_id} - {self.status}"


class ReportAttachment(BaseModel):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="attachments")
    type = models.CharField(max_length=16, choices=AttachmentType.choices)
    file = models.FileField(upload_to=report_upload_path)

    original_name = models.CharField(max_length=255, blank=True, default="")
    mime_type = models.CharField(max_length=100, blank=True, default="")
    file_size = models.BigIntegerField(default=0)

    def __str__(self):
        return f"{self.report_id} - {self.type}"
