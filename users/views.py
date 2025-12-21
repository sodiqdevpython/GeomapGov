from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import TelegramRegisterSerializer, UserMeSerializer

User = get_user_model()


class TelegramAuthView(APIView):
    """
    Telegram bot shu endpointga keladi:
    - User bo'lmasa yaratadi
    - Bo'lsa login qilib token qaytaradi

    username = str(telegram_id)
    password = str(telegram_id)
    """
    permission_classes = [AllowAny]

    def post(self, request):
        ser = TelegramRegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        telegram_id = ser.validated_data["telegram_id"]
        username = str(telegram_id)
        raw_password = str(telegram_id)

        user, created = User.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={
                "username": username,
                "first_name": ser.validated_data["first_name"],
                "last_name": ser.validated_data.get("last_name", ""),
                "phone_number": ser.validated_data["phone_number"],
            },
        )

        if created:
            user.set_password(raw_password)
            user.save(update_fields=["password"])
        else:
            # yangilash (telegram user data o'zgarishi mumkin)
            changed = False
            fn = ser.validated_data["first_name"]
            ln = ser.validated_data.get("last_name", "")
            ph = ser.validated_data["phone_number"]

            if user.first_name != fn:
                user.first_name = fn
                changed = True
            if user.last_name != ln:
                user.last_name = ln
                changed = True
            if user.phone_number != ph:
                user.phone_number = ph
                changed = True
            if user.username != username:
                user.username = username
                changed = True

            if changed:
                user.save()

        data = {
            "created": created,
            "tokens": user.token(),
            "user": UserMeSerializer(user).data,
        }
        return Response(data, status=status.HTTP_200_OK)


class MeView(APIView):
    def get(self, request):
        return Response(UserMeSerializer(request.user).data)
