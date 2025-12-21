from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class TelegramRegisterSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=32)

    def validate_phone_number(self, v: str) -> str:
        v = v.strip()
        if len(v) < 7:
            raise serializers.ValidationError("Telefon raqam noto‘g‘ri.")
        return v


class UserMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "phone_number", "telegram_id", "user_type")
