from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from django.contrib.auth import authenticate

from .models import AuthSession
from .serializers import serialize_auth_response, serialize_user

SESSION_TTL_HOURS = 8


def _is_expired(expires_at: datetime) -> bool:
	return datetime.now(timezone.utc) > expires_at


def _get_session(token: str) -> AuthSession | None:
	session = AuthSession.objects.select_related('user').filter(token=token).first()
	if not session:
		return None

	if _is_expired(session.expires_at):
		session.delete()
		return None

	return session


def login(username: str, password: str) -> dict | None:
	user = authenticate(username=username.strip(), password=password)
	if not user:
		return None

	# Only allow staff or superuser accounts to obtain a session token
	if not (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)):
		return {"not_authorized": True}

	token = uuid4().hex
	expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)
	AuthSession.objects.update_or_create(
		token=token,
		defaults={
			"user": user,
			"expires_at": expires_at,
		},
	)

	return serialize_auth_response(token, user)


def get_user_by_token(token: str) -> dict | None:
	session = _get_session(token)
	if not session:
		return None

	return serialize_user(session.user)


def get_user_object_by_token(token: str):
	session = _get_session(token)
	if not session:
		return None

	return session.user


def logout(token: str) -> bool:
	deleted, _ = AuthSession.objects.filter(token=token).delete()
	return bool(deleted)
