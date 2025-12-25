from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User


# ===== CREATE FORM =====
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "phone_number",
            "telegram_id",
            "user_type",
            "is_staff",
            "is_active",
        )


# ===== UPDATE FORM =====
class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    model = User

    # === LIST PAGE ===
    list_display = (
        "id",
        "username",
        "first_name",
        "last_name",
        "telegram_id",
        "phone_number",
        "user_type",
        "is_staff",
        "is_active",
    )

    search_fields = (
        "username",
        "first_name",
        "last_name",
        "phone_number",
        "telegram_id",
    )

    list_filter = (
        "user_type",
        "is_staff",
        "is_active",
    )

    ordering = ("-id",)

    # === EDIT USER PAGE ===
    fieldsets = (
        ("Asosiy ma’lumotlar", {
            "fields": (
                "username",
                "password",
            )
        }),
        ("Shaxsiy ma’lumotlar", {
            "fields": (
                "first_name",
                "last_name",
                "phone_number",
                "telegram_id",
            )
        }),
        ("Rollar va huquqlar", {
            "fields": (
                "user_type",
                "is_staff",
                "is_active",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Muhim sanalar", {
            "fields": (
                "last_login",
                "date_joined",
            )
        }),
    )

    # === CREATE USER PAGE ===
    add_fieldsets = (
        ("Yangi foydalanuvchi", {
            "classes": ("wide",),
            "fields": (
                "username",
                "first_name",
                "last_name",
                "phone_number",
                "telegram_id",
                "user_type",
                "password1",
                "password2",
                "is_staff",
                "is_active",
            ),
        }),
    )
