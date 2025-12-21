from django.db import models
from utils.models import BaseModel
from django.contrib.auth.models import AbstractUser
from .choices import UserChoices
from rest_framework_simplejwt.tokens import RefreshToken


class User(BaseModel, AbstractUser):
    user_type = models.CharField(
        max_length=16,
        choices=UserChoices.choices,
        default=UserChoices.REPORTER,
    )

    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=32, blank=True, default="")

    def __str__(self):
        return self.username

    def token(self):
        refresh = RefreshToken.for_user(self)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
