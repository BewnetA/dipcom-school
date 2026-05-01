from __future__ import annotations

from django.urls import path

from .views import AnalyticsOverviewView, analytics_health


urlpatterns = [
	path("", AnalyticsOverviewView.as_view(), name="analytics-overview"),
	path("health/", analytics_health, name="analytics-health"),
]
