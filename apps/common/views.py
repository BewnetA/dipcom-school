from __future__ import annotations

import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.auth.services import get_user_object_by_token
from .services import (
	get_common_health,
	get_common_meta,
	get_course_fees,
	get_feature_flags,
	set_course_fees,
)


class CommonMetaView(View):
	def get(self, _request):
		return JsonResponse(get_common_meta())


class CommonFlagsView(View):
	def get(self, _request):
		return JsonResponse(get_feature_flags())


@method_decorator(csrf_exempt, name="dispatch")
class CourseFeesSettingsView(View):
	def get(self, _request):
		return JsonResponse(get_course_fees())

	def post(self, request):
		auth_header = request.headers.get("Authorization", "")
		if not auth_header.startswith("Bearer "):
			return JsonResponse({"detail": "Missing bearer token"}, status=401)

		token = auth_header.replace("Bearer ", "", 1).strip()
		user = get_user_object_by_token(token)
		if not user:
			return JsonResponse({"detail": "Invalid or expired token"}, status=401)
		if not getattr(user, "is_superuser", False):
			return JsonResponse({"detail": "Forbidden"}, status=403)

		try:
			payload = json.loads(request.body.decode("utf-8") if request.body else "{}")
		except json.JSONDecodeError:
			return JsonResponse({"detail": "Invalid JSON payload"}, status=400)

		try:
			computer = int(payload.get("computer"))
			office = int(payload.get("office"))
		except (TypeError, ValueError):
			return JsonResponse({"detail": "computer and office must be numbers"}, status=400)

		if computer < 0 or office < 0:
			return JsonResponse({"detail": "Fees cannot be negative"}, status=400)

		updated = set_course_fees(computer=computer, office=office)
		return JsonResponse(updated, status=200)


def common_health(_request):
	return JsonResponse(get_common_health())
