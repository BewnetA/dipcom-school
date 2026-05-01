from __future__ import annotations

import json

from django.contrib.auth.models import User
from django.http import HttpRequest, JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

from .services import get_user_by_token, get_user_object_by_token, login, logout


def _parse_json_body(request: HttpRequest) -> dict:
	if not request.body:
		return {}

	try:
		return json.loads(request.body.decode("utf-8"))
	except json.JSONDecodeError:
		return {}


def _extract_bearer_token(request: HttpRequest) -> str | None:
	auth_header = request.headers.get("Authorization", "")
	if not auth_header.startswith("Bearer "):
		return None
	return auth_header.replace("Bearer ", "", 1).strip() or None


def _require_superuser(request: HttpRequest):
	token = _extract_bearer_token(request)
	if not token:
		return None, JsonResponse({"detail": "Missing bearer token"}, status=401)

	user = get_user_object_by_token(token)
	if not user:
		return None, JsonResponse({"detail": "Invalid or expired token"}, status=401)

	if not user.is_superuser:
		return None, JsonResponse({"detail": "Forbidden"}, status=403)

	return user, None


@method_decorator(csrf_exempt, name="dispatch")
class LoginView(View):
	def post(self, request: HttpRequest):
		payload = _parse_json_body(request)
		username = str(payload.get("username", ""))
		password = str(payload.get("password", ""))

		auth_result = login(username, password)
		if not auth_result:
			return JsonResponse({"detail": "Invalid credentials"}, status=401)

		# services.login may return a sentinel when authentication succeeded
		# but the account is not authorized to obtain a session (non-staff/non-superuser)
		if isinstance(auth_result, dict) and auth_result.get("not_authorized"):
			return JsonResponse({"detail": "Account not authorized to login"}, status=403)

		return JsonResponse(auth_result, status=200)


class MeView(View):
	def get(self, request: HttpRequest):
		token = _extract_bearer_token(request)
		if not token:
			return JsonResponse({"detail": "Missing bearer token"}, status=401)

		user = get_user_by_token(token)
		if not user:
			return JsonResponse({"detail": "Invalid or expired token"}, status=401)

		return JsonResponse({"user": user}, status=200)


@method_decorator(csrf_exempt, name="dispatch")
class LogoutView(View):
	def post(self, request: HttpRequest):
		token = _extract_bearer_token(request)
		if not token:
			return JsonResponse({"detail": "Missing bearer token"}, status=401)

		did_logout = logout(token)
		if not did_logout:
			return JsonResponse({"detail": "Invalid or expired token"}, status=401)

		return JsonResponse({"loggedOut": True}, status=200)


@method_decorator(csrf_exempt, name="dispatch")
class AdminManagementView(View):
	def get(self, request: HttpRequest):
		_superuser, error_response = _require_superuser(request)
		if error_response:
			return error_response

		admins = User.objects.filter(is_staff=True, is_superuser=False).order_by("username")

		query = str(request.GET.get("search", "")).strip()
		if query:
			admins = admins.filter(
				Q(username__icontains=query)
				| Q(email__icontains=query)
				| Q(first_name__icontains=query)
				| Q(last_name__icontains=query)
			)

		status_filter = str(request.GET.get("status", "")).strip().lower()
		if status_filter == "active":
			admins = admins.filter(is_active=True)
		elif status_filter == "inactive":
			admins = admins.filter(is_active=False)
		items = [
			{
				"id": user.id,
				"name": f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip() or user.username,
				"username": user.username,
				"email": user.email or "",
				"isActive": user.is_active,
				"role": "superadmin" if user.is_superuser else "staff",
			}
			for user in admins
		]
		return JsonResponse({"items": items, "count": len(items)})

	def post(self, request: HttpRequest):
		_superuser, error_response = _require_superuser(request)
		if error_response:
			return error_response

		payload = _parse_json_body(request)
		required_fields = ["username", "password", "email", "first_name", "last_name"]
		missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
		if missing:
			return JsonResponse({"detail": f"Missing required fields: {', '.join(missing)}"}, status=400)

		username = str(payload.get("username", "")).strip()
		if User.objects.filter(username=username).exists():
			return JsonResponse({"detail": "Username already exists"}, status=400)

		created = User.objects.create_user(
			username=username,
			password=str(payload.get("password", "")),
			email=str(payload.get("email", "")).strip(),
			first_name=str(payload.get("first_name", "")).strip(),
			last_name=str(payload.get("last_name", "")).strip(),
			is_staff=True,
			is_superuser=False,
		)

		return JsonResponse(
			{
				"id": created.id,
				"name": f"{created.first_name} {created.last_name}".strip() or created.username,
				"username": created.username,
				"email": created.email or "",
				"isActive": created.is_active,
				"role": "staff",
			},
			status=201,
		)


@method_decorator(csrf_exempt, name="dispatch")
class AdminManagementDetailView(View):
	def patch(self, request: HttpRequest, admin_id: int):
		_superuser, error_response = _require_superuser(request)
		if error_response:
			return error_response

		user = User.objects.filter(id=admin_id, is_staff=True, is_superuser=False).first()
		if not user:
			return JsonResponse({"detail": "Staff admin not found"}, status=404)

		payload = _parse_json_body(request)
		if "isActive" not in payload:
			return JsonResponse({"detail": "isActive is required"}, status=400)

		user.is_active = bool(payload.get("isActive"))
		user.save(update_fields=["is_active"])

		return JsonResponse(
			{
				"id": user.id,
				"name": f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip() or user.username,
				"username": user.username,
				"email": user.email or "",
				"isActive": user.is_active,
				"role": "staff",
			},
			status=200,
		)


def auth_health(_request: HttpRequest):
	return JsonResponse({"status": "ok", "module": "auth"})
