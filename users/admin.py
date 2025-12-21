from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "telegram_id", "first_name", "last_name", "phone_number", "user_type", "is_staff")
    search_fields = ("username", "telegram_id", "first_name", "last_name", "phone_number")
    list_filter = ("user_type", "is_staff", "is_active")
