import mimetypes
from rest_framework import serializers
from .models import Report, ReportAttachment
from .choices import AttachmentType, ReportStatus


class ReportAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ReportAttachment
        fields = ("id", "type", "file_url", "original_name", "mime_type", "file_size", "created_at")

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not obj.file:
            return None
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url


class ReportSerializer(serializers.ModelSerializer):
    attachments = ReportAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = (
            "id",
            "description",
            "latitude",
            "longitude",
            "status",
            "resolved_at",
            "created_at",
            "attachments",
        )
        read_only_fields = ("status", "resolved_at", "created_at", "attachments")

    def validate(self, attrs):
        lat = attrs.get("latitude")
        lon = attrs.get("longitude")
        if lat is None or lon is None:
            raise serializers.ValidationError("GPS (latitude/longitude) majburiy.")
        if not (-90 <= float(lat) <= 90):
            raise serializers.ValidationError("Latitude noto‘g‘ri.")
        if not (-180 <= float(lon) <= 180):
            raise serializers.ValidationError("Longitude noto‘g‘ri.")
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        report = Report.objects.create(user=user, **validated_data)

        # ixtiyoriy: bir so'rovda bir nechta fayl
        files = request.FILES.getlist("files")
        for f in files:
            mime, _ = mimetypes.guess_type(getattr(f, "name", "") or "")
            mime = mime or getattr(f, "content_type", "") or ""

            atype = AttachmentType.FILE
            if mime.startswith("image/"):
                atype = AttachmentType.IMAGE
            elif mime.startswith("video/"):
                atype = AttachmentType.VIDEO
            elif mime in ("audio/ogg", "audio/mpeg", "audio/wav") or mime.startswith("audio/"):
                atype = AttachmentType.VOICE

            ReportAttachment.objects.create(
                report=report,
                type=atype,
                file=f,
                original_name=getattr(f, "name", "") or "",
                mime_type=mime,
                file_size=getattr(f, "size", 0) or 0,
            )

        return report


class ReportCreateSerializer(serializers.ModelSerializer):
    """
    Create uchun alohida serializer:
    - status ni user qo'ymaydi
    - files multipart orqali keladi (files[])
    """
    class Meta:
        model = Report
        fields = ("description", "latitude", "longitude")


class ReportAttachmentCreateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=AttachmentType.choices)
    file = serializers.FileField()

    def create(self, validated_data):
        report = self.context["report"]
        f = validated_data["file"]
        mime = getattr(f, "content_type", "") or ""
        return ReportAttachment.objects.create(
            report=report,
            type=validated_data["type"],
            file=f,
            original_name=getattr(f, "name", "") or "",
            mime_type=mime,
            file_size=getattr(f, "size", 0) or 0,
        )
