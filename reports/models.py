from django.db import models
from django.conf import settings
from utils.models import BaseModel
from .choices import AttachmentType


# =========================
# Report Status
# =========================
class ReportStatus(models.TextChoices):
    NEW = "new", "New"
    SENT = "sent", "Sent to organization"
    READ = "read", "Read by organization"
    ACCEPTED = "accepted", "Accepted by organization"
    ASSIGNED = "assigned", "Assigned to staff"
    IN_PROGRESS = "in_progress", "In progress"
    RESOLVED = "resolved", "Resolved"
    REJECTED = "rejected", "Rejected"
    REDIRECTED = "redirected", "Redirected"


# =========================
# Upload path
# =========================
def report_upload_path(instance, filename: str) -> str:
    return f"reports/{instance.report_id}/{filename}"


# =========================
# Main Report
# =========================
class Report(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports"
    )

    description = models.TextField()

    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.NEW
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports"
    )

    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Report #{self.id} ({self.status})"

    def get_status_uz(self) -> str:
        """
        Statusni doim O'zbekcha qaytaradi.
        get_status_display ishlamagan holatlarda ham ishlaydi.
        """
        mapping = {
            ReportStatus.NEW: "Yangi",
            ReportStatus.SENT: "Tashkilotga yuborildi",
            ReportStatus.READ: "Tashkilot tomonidan o‘qildi",
            ReportStatus.ACCEPTED: "Tashkilot qabul qildi",
            ReportStatus.ASSIGNED: "Xodimga biriktirildi",
            ReportStatus.IN_PROGRESS: "Jarayonda",
            ReportStatus.RESOLVED: "Hal qilindi",
            ReportStatus.REJECTED: "Rad etildi",
            ReportStatus.REDIRECTED: "Yo‘naltirildi",
        }
        return mapping.get(self.status, str(self.status))


# =========================
# Attachments
# =========================
class ReportAttachment(BaseModel):
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="attachments"
    )

    type = models.CharField(max_length=16, choices=AttachmentType.choices)
    file = models.FileField(upload_to=report_upload_path)

    original_name = models.CharField(max_length=255, blank=True, default="")
    mime_type = models.CharField(max_length=100, blank=True, default="")
    file_size = models.BigIntegerField(default=0)

    def __str__(self):
        return f"{self.report_id} - {self.type}"


# =========================
# Organization reportni o‘qidi
# =========================
class ReportRead(models.Model):
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="reads"
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE
    )
    read_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("report", "organization")


# =========================
# Organization qabul qildi
# =========================
class ReportAcceptance(models.Model):
    report = models.OneToOneField(
        Report,
        on_delete=models.CASCADE,
        related_name="acceptance"
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    accepted_at = models.DateTimeField(auto_now_add=True)


# =========================
# Organization ichida yuklash
# =========================
class ReportAssignment(models.Model):
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="assignments"
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assigned_reports"
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assigned_by_me"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)


# =========================
# Boshqa organization ga yo‘naltirish
# =========================
class ReportRedirect(models.Model):
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="redirects"
    )
    from_organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="redirected_from"
    )
    to_organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="redirected_to"
    )
    reason = models.TextField()

    redirected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    redirected_at = models.DateTimeField(auto_now_add=True)
