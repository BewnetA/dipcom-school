from __future__ import annotations

from django.urls import path

from .views import CommonFlagsView, CommonMetaView, common_health


urlpatterns = [
	path("meta/", CommonMetaView.as_view(), name="common-meta"),
	path("flags/", CommonFlagsView.as_view(), name="common-flags"),
	path("health/", common_health, name="common-health"),
]
