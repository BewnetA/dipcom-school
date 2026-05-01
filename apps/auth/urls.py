from __future__ import annotations

from django.urls import path

from .views import AdminManagementView, LoginView, LogoutView, MeView, auth_health


urlpatterns = [
	path("login/", LoginView.as_view(), name="auth-login"),
	path("me/", MeView.as_view(), name="auth-me"),
	path("logout/", LogoutView.as_view(), name="auth-logout"),
	path("health/", auth_health, name="auth-health"),
	path("admins/", AdminManagementView.as_view(), name="auth-admins"),
]
