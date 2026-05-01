from __future__ import annotations

from copy import deepcopy


def serialize_landing_content(payload: dict) -> dict:
	return deepcopy(payload)


def serialize_registration(item: dict) -> dict:
	return deepcopy(item)


def serialize_registrations(items: list[dict]) -> list[dict]:
	return [serialize_registration(item) for item in items]
