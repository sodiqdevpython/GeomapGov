from django.urls import path
from .views import OrganizationListApiView

urlpatterns = [
    path("organizations/", OrganizationListApiView.as_view(), name="org-list"),
]
