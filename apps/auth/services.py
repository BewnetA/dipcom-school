from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from django.contrib.auth import authenticate, get_user_model

from .serializers import serialize_auth_response, serialize_user

SESSION_TTL_HOURS = 8
_session_store: dict[str, dict] = {}


def _is_expired(expires_at: datetime) -> bool:
	return datetime.now(timezone.utc) > expires_at


def login(username: str, password: str) -> dict | None:
	user = authenticate(username=username.strip(), password=password)
	if not user:
		return None

	# Only allow staff or superuser accounts to obtain a session token
	if not (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)):
		return {"not_authorized": True}

	token = uuid4().hex
	expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)
	_session_store[token] = {
		"userId": str(user.pk),
		"expiresAt": expires_at,
	}

	return serialize_auth_response(token, user)


def get_user_by_token(token: str) -> dict | None:
	session = _session_store.get(token)
	if not session:
		return None

	if _is_expired(session["expiresAt"]):
		_session_store.pop(token, None)
		return None

	User = get_user_model()
	user = User.objects.filter(pk=session["userId"]).first()
	if not user:
		return None

	return serialize_user(user)


def get_user_object_by_token(token: str):
	session = _session_store.get(token)
	if not session:
		return None

	if _is_expired(session["expiresAt"]):
		_session_store.pop(token, None)
		return None

	User = get_user_model()
	return User.objects.filter(pk=session["userId"]).first()


def logout(token: str) -> bool:
	if token in _session_store:
		_session_store.pop(token, None)
		return True
	return False
