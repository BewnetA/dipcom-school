from __future__ import annotations

from django.urls import path

from .views import AdminManagementDetailView, AdminManagementView


urlpatterns = [
	path("", AdminManagementView.as_view(), name="admins-collection"),
	path("<int:admin_id>/", AdminManagementDetailView.as_view(), name="admins-detail"),
]
