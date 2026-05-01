from __future__ import annotations

from django.http import JsonResponse
from django.urls import path

from .views import DashboardOverviewView


def dashboard_health(_request):
	return JsonResponse({"status": "ok", "module": "dashboard"})


urlpatterns = [
	path("", DashboardOverviewView.as_view(), name="dashboard-overview"),
	path("health/", dashboard_health, name="dashboard-health"),
]
