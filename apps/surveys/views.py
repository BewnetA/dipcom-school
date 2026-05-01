from __future__ import annotations

import json

from django.http import HttpRequest, HttpResponseNotAllowed, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

from .services import (
	create_survey,
	delete_survey,
	get_survey_by_id,
	get_survey_stats,
	list_surveys,
	send_survey_again,
	update_survey,
)


def _parse_json_body(request: HttpRequest) -> dict:
	if not request.body:
		return {}

	try:
		return json.loads(request.body.decode("utf-8"))
	except json.JSONDecodeError:
		return {}


@method_decorator(csrf_exempt, name="dispatch")
class SurveysCollectionView(View):
	def get(self, _request: HttpRequest):
		items = list_surveys()
		return JsonResponse({"items": items, "count": len(items)})

	def post(self, request: HttpRequest):
		payload = _parse_json_body(request)
		created = create_survey(payload)
		return JsonResponse(created, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class SurveyDetailView(View):
	def get(self, _request: HttpRequest, survey_id: str):
		survey = get_survey_by_id(survey_id)
		if not survey:
			return JsonResponse({"detail": "Survey not found"}, status=404)
		return JsonResponse(survey)

	def put(self, request: HttpRequest, survey_id: str):
		payload = _parse_json_body(request)
		updated = update_survey(survey_id, payload)
		if not updated:
			return JsonResponse({"detail": "Survey not found"}, status=404)
		return JsonResponse(updated)

	def patch(self, request: HttpRequest, survey_id: str):
		return self.put(request, survey_id)

	def delete(self, _request: HttpRequest, survey_id: str):
		deleted = delete_survey(survey_id)
		if not deleted:
			return JsonResponse({"detail": "Survey not found"}, status=404)
		return JsonResponse({"deleted": True})

	def post(self, _request: HttpRequest, _survey_id: str):
		return HttpResponseNotAllowed(["GET", "PUT", "PATCH", "DELETE"])


@method_decorator(csrf_exempt, name="dispatch")
class SurveyStatsView(View):
	def get(self, _request: HttpRequest, survey_id: str):
		stats = get_survey_stats(survey_id)
		if not stats:
			return JsonResponse({"detail": "Survey not found"}, status=404)
		return JsonResponse(stats)


@method_decorator(csrf_exempt, name="dispatch")
class SurveySendAgainView(View):
	def post(self, _request: HttpRequest, survey_id: str):
		result = send_survey_again(survey_id)
		if not result:
			return JsonResponse({"detail": "Survey not found"}, status=404)
		return JsonResponse(result)
