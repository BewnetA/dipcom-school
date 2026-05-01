from __future__ import annotations

import json

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

from .services import create_registration, get_landing_content, list_registrations


def _parse_json_body(request: HttpRequest) -> dict:
	if not request.body:
		return {}

	try:
		return json.loads(request.body.decode("utf-8"))
	except json.JSONDecodeError:
		return {}


class LandingContentView(View):
	def get(self, _request: HttpRequest):
		return JsonResponse(get_landing_content())


@method_decorator(csrf_exempt, name="dispatch")
class LandingRegistrationsView(View):
	def get(self, _request: HttpRequest):
		items = list_registrations()
		return JsonResponse({"items": items, "count": len(items)})

	def post(self, request: HttpRequest):
		payload = _parse_json_body(request)
		required = ["name", "phone", "batchId"]
		if any(not str(payload.get(field, "")).strip() for field in required):
			return JsonResponse({"detail": "name, phone, and batchId are required"}, status=400)

		try:
			created = create_registration(payload)
		except ValueError as exc:
			return JsonResponse({"detail": str(exc)}, status=400)
		return JsonResponse(created, status=201)


def landing_health(_request: HttpRequest):
	return JsonResponse({"status": "ok", "module": "landing"})
