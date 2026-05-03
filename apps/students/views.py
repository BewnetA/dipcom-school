from __future__ import annotations

import json

from django.http import HttpRequest, HttpResponseNotAllowed, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

from .services import (
	create_student,
	delete_student,
	get_student_by_id,
	get_students_summary,
	list_students,
	list_approval_students,
	update_student,
)
from apps.auth.services import get_user_object_by_token


def _extract_bearer_token(request: HttpRequest) -> str | None:
	auth_header = request.headers.get("Authorization", "")
	if not auth_header.startswith("Bearer "):
		return None
	return auth_header.replace("Bearer ", "", 1).strip() or None


def _require_staff_or_superuser(request: HttpRequest):
	token = _extract_bearer_token(request)
	if not token:
		return None, JsonResponse({"detail": "Missing bearer token"}, status=401)

	user = get_user_object_by_token(token)
	if not user:
		return None, JsonResponse({"detail": "Invalid or expired token"}, status=401)

	if not (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)):
		return None, JsonResponse({"detail": "Forbidden"}, status=403)

	return user, None


def _extract_filters(request: HttpRequest) -> dict:
	return {
		"search": request.GET.get("search"),
		"batchId": request.GET.get("batchId"),
		"paymentStatus": request.GET.get("paymentStatus"),
		"employmentStatus": request.GET.get("employmentStatus"),
		"gradeBand": request.GET.get("gradeBand"),
		"graduated": request.GET.get("graduated"),
	}


def _parse_json_body(request: HttpRequest) -> dict:
	if not request.body:
		return {}

	try:
		return json.loads(request.body.decode("utf-8"))
	except json.JSONDecodeError:
		return {}


@method_decorator(csrf_exempt, name="dispatch")
class StudentsCollectionView(View):
	def get(self, request: HttpRequest):
		filters = _extract_filters(request)

		# default students list to approved only (students page should show only approved)
		if not filters.get("status"):
			filters["status"] = "approved"
		items = list_students(filters)
		return JsonResponse({"items": items, "count": len(items)})

	def post(self, request: HttpRequest):
		payload = _parse_json_body(request)
		try:
			created = create_student(payload)
		except ValueError as exc:
			return JsonResponse({"detail": str(exc)}, status=400)
		return JsonResponse(created, status=201)


class StudentsSummaryView(View):
	def get(self, request: HttpRequest):
		filters = _extract_filters(request)
		summary = get_students_summary(filters)
		return JsonResponse(summary)


class PendingStudentsView(View):
	def get(self, request: HttpRequest):
		items = list_approval_students(search=request.GET.get("search"))
		return JsonResponse({"items": items, "count": len(items)})


@csrf_exempt
def approve_student(request: HttpRequest, student_id: str):
	if request.method != "POST":
		return HttpResponseNotAllowed(["POST"])

	_user, error = _require_staff_or_superuser(request)
	if error:
		return error

	student = get_student_by_id(student_id)
	if not student:
		return JsonResponse({"detail": "Student not found"}, status=404)

	# only allow approving pending online registrations from the web approvals page
	if student.get("registrationType") != "online" or student.get("status") != "pending":
		return JsonResponse({"detail": "Student cannot be approved"}, status=400)

	updated = update_student(student_id, {"status": "approved"})
	return JsonResponse(updated, status=200)

@method_decorator(csrf_exempt, name="dispatch")
class StudentDetailView(View):
	def get(self, _request: HttpRequest, student_id: str):
		student = get_student_by_id(student_id)
		if not student:
			return JsonResponse({"detail": "Student not found"}, status=404)
		return JsonResponse(student)

	def put(self, request: HttpRequest, student_id: str):
		payload = _parse_json_body(request)
		try:
			updated = update_student(student_id, payload)
		except ValueError as exc:
			return JsonResponse({"detail": str(exc)}, status=400)
		if not updated:
			return JsonResponse({"detail": "Student not found"}, status=404)
		return JsonResponse(updated)

	def patch(self, request: HttpRequest, student_id: str):
		return self.put(request, student_id)

	def delete(self, _request: HttpRequest, student_id: str):
		deleted = delete_student(student_id)
		if not deleted:
			return JsonResponse({"detail": "Student not found"}, status=404)
		return JsonResponse({"deleted": True})

	def post(self, _request: HttpRequest, _student_id: str):
		return HttpResponseNotAllowed(["GET", "PUT", "PATCH", "DELETE"])
