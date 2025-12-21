from django.db import models

class ReportStatus(models.TextChoices):
    NEW = "new", "New"
    IN_PROGRESS = "in_progress", "In progress"
    RESOLVED = "resolved", "Resolved"
    REJECTED = "rejected", "Rejected"


class AttachmentType(models.TextChoices):
    IMAGE = "image", "Image"
    VIDEO = "video", "Video"
    VOICE = "voice", "Voice"
    FILE = "file", "File"
