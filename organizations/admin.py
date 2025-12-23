from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import Organization, OrganizationMember

User = get_user_model()


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name", "description")
    list_filter = ("is_active",)
    ordering = ("-created_at",)


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "role", "joined_at")
    list_filter = ("role", "organization")
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "organization__name",
    )

    # 🔥 ENG MUHIM QATOR
    autocomplete_fields = ("user", "organization")
