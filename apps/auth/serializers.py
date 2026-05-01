from __future__ import annotations

from copy import deepcopy


def serialize_user(user) -> dict:
	if hasattr(user, "pk"):
		name = (getattr(user, "first_name", "") or "").strip()
		last_name = (getattr(user, "last_name", "") or "").strip()
		display_name = f"{name} {last_name}".strip() or getattr(user, "username", "")
		role = "superadmin" if getattr(user, "is_superuser", False) else "staff" if getattr(user, "is_staff", False) else "user"
		return {
			"id": str(user.pk),
			"username": getattr(user, "username", ""),
			"name": display_name,
			"role": role,
			"email": getattr(user, "email", "") or None,
		}

	safe = deepcopy(user)
	safe.pop("password", None)
	return safe


def serialize_auth_response(token: str, user: dict) -> dict:
	return {
		"token": token,
		"tokenType": "Bearer",
		"user": serialize_user(user),
	}
