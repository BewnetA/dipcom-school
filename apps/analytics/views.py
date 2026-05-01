from __future__ import annotations

from django.http import JsonResponse
from django.views import View

from .services import get_analytics_overview


class AnalyticsOverviewView(View):
	def get(self, _request):
		payload = get_analytics_overview()
		return JsonResponse(payload)


def analytics_health(_request):
	return JsonResponse({"status": "ok", "module": "analytics"})
