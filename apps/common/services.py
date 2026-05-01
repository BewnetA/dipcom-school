from __future__ import annotations

from datetime import datetime, timezone

from .dummy_data import COMMON_FEATURE_FLAGS, COMMON_META
from .serializers import serialize_flags, serialize_meta


def get_common_meta() -> dict:
	return serialize_meta(COMMON_META)


def get_feature_flags() -> dict:
	return serialize_flags(COMMON_FEATURE_FLAGS)


def get_common_health() -> dict:
	return {
		"status": "ok",
		"module": "common",
		"timestamp": datetime.now(timezone.utc).isoformat(),
	}
