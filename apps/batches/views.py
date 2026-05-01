from __future__ import annotations

import json

from django.http import HttpRequest, HttpResponseNotAllowed, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

from .services import (
	create_batch,
	delete_batch,
	get_batch_by_id,
	list_batches,
	update_batch,
)


def _parse_json_body(request: HttpRequest) -> dict:
	if not request.body:
		return {}

	try:
		return json.loads(request.body.decode("utf-8"))
	except json.JSONDecodeError:
		return {}


@method_decorator(csrf_exempt, name="dispatch")
class BatchesCollectionView(View):
	def get(self, request: HttpRequest):
		active_only = str(request.GET.get("activeOnly", "")).lower() in {"1", "true", "yes"}
		items = list_batches(active_only=active_only)
		return JsonResponse({"items": items, "count": len(items)})

	def post(self, request: HttpRequest):
		payload = _parse_json_body(request)
		try:
			created = create_batch(payload)
		except ValueError as exc:
			return JsonResponse({"detail": str(exc)}, status=400)
		return JsonResponse(created, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class BatchDetailView(View):
	def get(self, request: HttpRequest, batch_id: str):
		query = request.GET.get("search")
		batch = get_batch_by_id(batch_id, student_search=query)
		if not batch:
			return JsonResponse({"detail": "Batch not found"}, status=404)
		return JsonResponse(batch)

	def put(self, request: HttpRequest, batch_id: str):
		payload = _parse_json_body(request)
		try:
			updated = update_batch(batch_id, payload)
		except ValueError as exc:
			return JsonResponse({"detail": str(exc)}, status=400)
		if not updated:
			return JsonResponse({"detail": "Batch not found"}, status=404)
		return JsonResponse(updated)

	def patch(self, request: HttpRequest, batch_id: str):
		return self.put(request, batch_id)

	def delete(self, _request: HttpRequest, batch_id: str):
		deleted = delete_batch(batch_id)
		if not deleted:
			return JsonResponse({"detail": "Batch not found"}, status=404)
		return JsonResponse({"deleted": True})

	def post(self, _request: HttpRequest, _batch_id: str):
		return HttpResponseNotAllowed(["GET", "PUT", "PATCH", "DELETE"])
