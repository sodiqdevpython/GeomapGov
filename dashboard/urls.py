from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("sign-in/", views.sign_in, name="sign_in"),
    path("shikoyatlar/", views.complaints_list, name="complaints"),
    path("organizations/", views.organizations_list, name="organizations"),
    path("organizations/<int:pk>/", views.organization_detail, name="organization_detail"),
    path("users/", views.users_list, name="users"),
    path("users/<uuid:pk>/", views.user_detail, name="user_detail"),
    path("shikoyatlar/<uuid:pk>/", views.report_detail, name="report_detail")
]
