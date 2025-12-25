from rest_framework import generics, permissions
from rest_framework.pagination import PageNumberPagination
from .models import Organization
from .serializers import OrganizationListSerializer

class OrgPagination(PageNumberPagination):
    page_size = 8                # keyboard uchun qulay
    page_size_query_param = "page_size"
    max_page_size = 50

class OrganizationListApiView(generics.ListAPIView):
    serializer_class = OrganizationListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = OrgPagination

    def get_queryset(self):
        qs = Organization.objects.all().order_by("name")
        # agar sizda is_active bo‘lsa:
        # qs = qs.filter(is_active=True)
        return qs
