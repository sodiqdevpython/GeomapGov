from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import handler404
from django.shortcuts import render

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from dashboard.views import custom_404_view

from dashboard.views import reports_map_view
from django.views.generic import TemplateView

schema_view = get_schema_view(
   openapi.Info(
      title="API",
      default_version='v1',
      description="Backend project",
      terms_of_service="sodiqdev.netlify.app",
      contact=openapi.Contact(email="sodiqdevpython@gmail.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=[permissions.AllowAny]
)

handler404 = custom_404_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", include("users.urls")),
    path("api/", include("reports.urls")),
    path("api/", include("organizations.urls")),
    path("", include("dashboard.urls")),
   
    
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path("reports-map/", reports_map_view, name="reports_map"),
    path(
        "webapp/location-picker/",
        TemplateView.as_view(template_name="webapp/location_picker.html"),
        name="webapp_location_picker",
    ),

]

if settings.DEBUG:
	urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
	urlpatterns += static(settings.STATIC_URL, document_root = settings.STATIC_ROOT)