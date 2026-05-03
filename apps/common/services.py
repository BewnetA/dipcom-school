from __future__ import annotations

from datetime import datetime, timezone

from .dummy_data import COMMON_FEATURE_FLAGS, COMMON_META
from .models import SystemSetting
from .serializers import serialize_flags, serialize_meta


COURSE_FEES_SETTING_KEY = "course_fees"
DEFAULT_COURSE_FEES = {"computer": 12000, "office": 12000}


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


def get_course_fees() -> dict:
	setting = SystemSetting.objects.filter(key=COURSE_FEES_SETTING_KEY).first()
	if not setting or not isinstance(setting.value_json, dict):
		return dict(DEFAULT_COURSE_FEES)

	stored = setting.value_json
	return {
		"computer": int(stored.get("computer", DEFAULT_COURSE_FEES["computer"])),
		"office": int(stored.get("office", DEFAULT_COURSE_FEES["office"])),
	}


def set_course_fees(computer: int, office: int) -> dict:
	cleaned = {"computer": int(computer), "office": int(office)}
	SystemSetting.objects.update_or_create(
		key=COURSE_FEES_SETTING_KEY,
		defaults={"value_json": cleaned},
	)
	return cleaned
