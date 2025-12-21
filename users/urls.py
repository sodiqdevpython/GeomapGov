from django.urls import path
from .views import TelegramAuthView, MeView

urlpatterns = [
    path("auth/telegram/", TelegramAuthView.as_view(), name="auth-telegram"),
    path("me/", MeView.as_view(), name="me"),
]
