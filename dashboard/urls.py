from django.urls import path
from . import views, organization_admin
from django.contrib.auth.views import LogoutView

app_name = "dashboard"

urlpatterns = [
    path("", views.superadmin_dashboard, name="home"),
    path("login/", views.sign_in, name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("shikoyatlar/", views.complaints_list, name="complaints"),
    path("organizations/", views.organizations_list, name="organizations"),
    path("organizations/<int:pk>/", views.organization_detail, name="organization_detail"),
    path("users/", views.users_list, name="users"),
    path("users/<uuid:pk>/", views.user_detail, name="user_detail"),
    path("shikoyatlar/<uuid:pk>/", views.report_detail, name="report_detail"),
    path("report/<uuid:pk>/", views.report_detail_json, name="report_detail_json"),

    path("org/", organization_admin.organization_admin_dashboard, name="org-dashboard"),
    path("org-admin/users/", organization_admin.org_users_list, name="org_users"),
    path("org-admin/reports/", views.org_reports_list, name="org_reports"),
    path("org-admin/reports/<uuid:pk>/", views.org_report_detail, name="org_report_detail"),
]
