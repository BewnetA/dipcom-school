from __future__ import annotations

from copy import deepcopy


def serialize_analytics_payload(payload: dict) -> dict:
	return deepcopy(payload)
