from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import datetime, time
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Report
from .choices import ReportStatus
from .serializers import (
    ReportSerializer,
    ReportCreateSerializer,
    ReportAttachmentCreateSerializer,
)
from .permissions import IsOwner
from users.choices import UserChoices



class ReportCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReportCreateSerializer
    parser_classes = (MultiPartParser, FormParser)

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        report_obj = ser.save()

        return Response(
            ReportSerializer(report_obj, context={"request": request}).data,
            status=status.HTTP_201_CREATED
        )


class MyReportsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReportSerializer

    def get_queryset(self):
        return (
            Report.objects.filter(user=self.request.user)
            .exclude(status=ReportStatus.RESOLVED)
            .order_by("-created_at")
        )


class MyResolvedReportsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReportSerializer

    def get_queryset(self):
        return (
            Report.objects.filter(user=self.request.user)
            .filter(status__in=[ReportStatus.RESOLVED, "RESOLVED", "done", "DONE"])
            .order_by("-resolved_at", "-created_at")
        )



class ReportDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsOwner]
    serializer_class = ReportSerializer
    queryset = Report.objects.all()


class ReportAddAttachmentView(APIView):
    """
    POST /api/reports/<id>/attachments/
    multipart/form-data:
      type: image|video|voice|file
      file: <binary>
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            report = Report.objects.get(pk=pk, user=request.user)
        except Report.DoesNotExist:
            return Response({"detail": "Report topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        ser = ReportAttachmentCreateSerializer(data=request.data, context={"report": report})
        ser.is_valid(raise_exception=True)
        attachment = ser.save()

        return Response({"attachment_id": str(attachment.id)}, status=status.HTTP_201_CREATED)


class ReportResolveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if getattr(request.user, "user_type", None) != UserChoices.REPORTER:
            return Response({"detail": "Sizda bunga ruxsat yo'q."}, status=status.HTTP_403_FORBIDDEN)

        try:
            report = Report.objects.get(pk=pk, user=request.user)
        except Report.DoesNotExist:
            return Response({"detail": "Report topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        if report.status == ReportStatus.RESOLVED:
            return Response({"detail": "Bu murojaat allaqachon hal qilingan."}, status=status.HTTP_400_BAD_REQUEST)

        report.status = ReportStatus.RESOLVED
        report.resolved_at = timezone.now()
        report.save(update_fields=["status", "resolved_at", "updated_at"])

        # ✅ created_at date bo‘lsa -> datetime ga aylantirib hisoblaymiz
        created_at = report.created_at
        resolved_at = report.resolved_at

        # created_at: date bo‘lsa (datetime emas)
        if hasattr(created_at, "year") and not hasattr(created_at, "hour"):
            created_dt = timezone.make_aware(datetime.combine(created_at, time.min))
        else:
            created_dt = created_at

        # resolved_at ham date bo‘lib qolsa (ehtiyot)
        if hasattr(resolved_at, "year") and not hasattr(resolved_at, "hour"):
            resolved_dt = timezone.make_aware(datetime.combine(resolved_at, time.min))
        else:
            resolved_dt = resolved_at

        resolution_seconds = int((resolved_dt - created_dt).total_seconds())

        data = {
            "report": ReportSerializer(report, context={"request": request}).data,
            "resolution_seconds": resolution_seconds,
        }
        return Response(data, status=status.HTTP_200_OK)


class GuideView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "title": "Ishlatish bo‘yicha qo‘llanma",
            "steps": [
                "1) Murojat yuborish bo‘limini tanlang",
                "2) Muammoni matn ko‘rinishida yozing",
                "3) Xohlasangiz rasm/video/ovoz/file yuboring",
                "4) GPS joylashuvni yuboring",
                "5) Yuborilgach, murojaat ro‘yxatingizda ko‘rinadi",
                "6) Muammo hal bo‘lgach, murojaatni tanlab: ✅ Hal bo‘ldi tugmasini bosing",
            ]
        })
