from __future__ import annotations

from copy import deepcopy


def serialize_survey(survey: dict) -> dict:
	return deepcopy(survey)


def serialize_surveys(surveys: list[dict]) -> list[dict]:
	return [serialize_survey(survey) for survey in surveys]


def serialize_response_stats(survey: dict) -> dict:
	yes_count = int(survey.get("responses", {}).get("yes", 0))
	no_count = int(survey.get("responses", {}).get("no", 0))
	total = yes_count + no_count

	return {
		"id": survey.get("id"),
		"question": survey.get("question"),
		"yes": yes_count,
		"no": no_count,
		"total": total,
		"yesRate": round((yes_count / total) * 100) if total else 0,
		"noRate": round((no_count / total) * 100) if total else 0,
	}
