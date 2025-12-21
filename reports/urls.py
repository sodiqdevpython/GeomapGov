from django.urls import path
from .views import (
    ReportCreateView,
    MyReportsView,
    MyResolvedReportsView,
    ReportDetailView,
    ReportAddAttachmentView,
    ReportResolveView,
    GuideView,
)

urlpatterns = [
    path("reports/", ReportCreateView.as_view(), name="report-create"),
    path("reports/mine/", MyReportsView.as_view(), name="my-reports"),
    path("reports/mine/resolved/", MyResolvedReportsView.as_view(), name="my-reports-resolved"),
    path("reports/<uuid:pk>/", ReportDetailView.as_view(), name="report-detail"),
    path("reports/<uuid:pk>/attachments/", ReportAddAttachmentView.as_view(), name="report-add-attachment"),
    path("reports/<uuid:pk>/resolve/", ReportResolveView.as_view(), name="report-resolve"),
    path("guide/", GuideView.as_view(), name="guide"),
]
