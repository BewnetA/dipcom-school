from __future__ import annotations

from django.http import JsonResponse
from django.views import View

from .services import get_dashboard_overview


class DashboardOverviewView(View):
	def get(self, request):
		payload = get_dashboard_overview()
		return JsonResponse(payload)
