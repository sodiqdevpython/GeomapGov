from django.contrib import admin
from .models import Report, ReportAttachment

class ReportAttachmentInline(admin.TabularInline):
    model = ReportAttachment
    extra = 0

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "latitude", "longitude", "created_at", "resolved_at")
    list_filter = ("status", "created_at")
    search_fields = ("id", "user__username", "description")
    inlines = [ReportAttachmentInline]

@admin.register(ReportAttachment)
class ReportAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "report", "type", "original_name", "file_size", "created_at")
    list_filter = ("type", "created_at")
