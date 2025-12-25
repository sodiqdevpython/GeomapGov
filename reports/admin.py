from django.contrib import admin
from django.utils.html import format_html
from django.utils.timezone import localtime

from .models import (
    Report,
    ReportAttachment,
    ReportRead,
    ReportAcceptance,
    ReportAssignment,
    ReportRedirect,
)
from .models import ReportStatus


# =========================
# Inlines
# =========================
class ReportAttachmentInline(admin.TabularInline):
    model = ReportAttachment
    extra = 0
    readonly_fields = (
        "type",
        "original_name",
        "mime_type",
        "file_size",
        "file_link",
        "created_at",
    )

    def file_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">📎 Faylni ochish</a>',
                obj.file.url
            )
        return "-"
    file_link.short_description = "Fayl"


class ReportReadInline(admin.TabularInline):
    model = ReportRead
    extra = 0
    readonly_fields = ("organization", "read_by", "read_at")


class ReportAcceptanceInline(admin.StackedInline):
    model = ReportAcceptance
    extra = 0
    readonly_fields = ("organization", "accepted_by", "accepted_at")


class ReportAssignmentInline(admin.TabularInline):
    model = ReportAssignment
    extra = 0
    readonly_fields = (
        "organization",
        "assigned_to",
        "assigned_by",
        "assigned_at",
    )


class ReportRedirectInline(admin.StackedInline):
    model = ReportRedirect
    extra = 0
    readonly_fields = (
        "from_organization",
        "to_organization",
        "reason",
        "redirected_by",
        "redirected_at",
    )


# =========================
# Main Report Admin
# =========================
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "organization",
        "colored_status",
        "short_description",
        "location",
        "created_at",
    )

    list_filter = (
        "status",
        "organization",
        "created_at",
    )

    search_fields = (
        "id",
        "description",
        "user__username",
        "organization__name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "resolved_at",
    )

    fieldsets = (
        ("Asosiy ma’lumotlar", {
            "fields": (
                "user",
                "organization",
                "status",
                "description",
            )
        }),
        ("Joylashuv", {
            "fields": (
                ("latitude", "longitude"),
            )
        }),
        ("Vaqtlar", {
            "fields": (
                "created_at",
                "updated_at",
                "resolved_at",
            )
        }),
    )

    inlines = (
        ReportAttachmentInline,
        ReportReadInline,
        ReportAcceptanceInline,
        ReportAssignmentInline,
        ReportRedirectInline,
    )

    ordering = ("-created_at",)

    list_per_page = 25

    # =========================
    # Custom columns
    # =========================
    def colored_status(self, obj):
        colors = {
            ReportStatus.NEW: "#6c757d",
            ReportStatus.SENT: "#0d6efd",
            ReportStatus.READ: "#6610f2",
            ReportStatus.ACCEPTED: "#198754",
            ReportStatus.ASSIGNED: "#20c997",
            ReportStatus.IN_PROGRESS: "#ffc107",
            ReportStatus.RESOLVED: "#198754",
            ReportStatus.REJECTED: "#dc3545",
            ReportStatus.REDIRECTED: "#fd7e14",
        }
        color = colors.get(obj.status, "#000")
        return format_html(
            '<b style="color:{};">{}</b>',
            color,
            obj.get_status_uz()
        )
    colored_status.short_description = "Holati"

    def short_description(self, obj):
        return obj.description[:60] + "..." if len(obj.description) > 60 else obj.description
    short_description.short_description = "Tavsif"

    def location(self, obj):
        return f"{obj.latitude}, {obj.longitude}"
    location.short_description = "Koordinata"


# =========================
# Standalone Admins (ixtiyoriy)
# =========================
@admin.register(ReportAttachment)
class ReportAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "report", "type", "original_name", "created_at")
    search_fields = ("original_name",)
    list_filter = ("type",)


@admin.register(ReportRead)
class ReportReadAdmin(admin.ModelAdmin):
    list_display = ("report", "organization", "read_by", "read_at")
    list_filter = ("organization",)


@admin.register(ReportAcceptance)
class ReportAcceptanceAdmin(admin.ModelAdmin):
    list_display = ("report", "organization", "accepted_by", "accepted_at")


@admin.register(ReportAssignment)
class ReportAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "report",
        "organization",
        "assigned_to",
        "assigned_by",
        "assigned_at",
    )


@admin.register(ReportRedirect)
class ReportRedirectAdmin(admin.ModelAdmin):
    list_display = (
        "report",
        "from_organization",
        "to_organization",
        "redirected_by",
        "redirected_at",
    )
