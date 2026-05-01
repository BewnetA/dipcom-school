from __future__ import annotations

from django.urls import path

from .views import LandingContentView, LandingRegistrationsView, landing_health


urlpatterns = [
	path("", LandingContentView.as_view(), name="landing-content"),
	path("registrations/", LandingRegistrationsView.as_view(), name="landing-registrations"),
	path("health/", landing_health, name="landing-health"),
]
