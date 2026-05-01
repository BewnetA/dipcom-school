from __future__ import annotations

from datetime import date
from uuid import uuid4

from .models import Survey
from .serializers import serialize_response_stats, serialize_survey, serialize_surveys


def _survey_to_dict(survey: Survey) -> dict:
	return {
		"id": survey.id,
		"question": survey.question,
		"type": survey.survey_type,
		"lastSent": survey.last_sent.isoformat(),
		"responses": {
			"yes": int(survey.response_yes),
			"no": int(survey.response_no),
		},
	}


def list_surveys() -> list[dict]:
	items = [_survey_to_dict(survey) for survey in Survey.objects.all()]
	return serialize_surveys(items)


def get_survey_by_id(survey_id: str) -> dict | None:
	survey = Survey.objects.filter(id=survey_id).first()
	if not survey:
		return None
	return serialize_survey(_survey_to_dict(survey))


def get_survey_stats(survey_id: str) -> dict | None:
	survey = Survey.objects.filter(id=survey_id).first()
	if not survey:
		return None
	return serialize_response_stats(_survey_to_dict(survey))


def create_survey(payload: dict) -> dict:
	survey_id = payload.get("id") or f"q-{uuid4().hex[:8]}"
	while Survey.objects.filter(id=survey_id).exists():
		survey_id = f"q-{uuid4().hex[:8]}"

	responses = payload.get("responses", {})
	survey = Survey.objects.create(
		id=survey_id,
		question=payload.get("question", ""),
		survey_type=payload.get("type", "yes_no"),
		last_sent=payload.get("lastSent") or str(date.today()),
		response_yes=int(responses.get("yes", 0)),
		response_no=int(responses.get("no", 0)),
	)
	return serialize_survey(_survey_to_dict(survey))


def update_survey(survey_id: str, payload: dict) -> dict | None:
	survey = Survey.objects.filter(id=survey_id).first()
	if not survey:
		return None

	if "question" in payload:
		survey.question = payload["question"]
	if "type" in payload:
		survey.survey_type = payload["type"]
	if "lastSent" in payload:
		survey.last_sent = payload["lastSent"]

	if "responses" in payload and isinstance(payload["responses"], dict):
		survey.response_yes = int(payload["responses"].get("yes", survey.response_yes))
		survey.response_no = int(payload["responses"].get("no", survey.response_no))

	survey.save()
	return serialize_survey(_survey_to_dict(survey))


def delete_survey(survey_id: str) -> bool:
	deleted, _ = Survey.objects.filter(id=survey_id).delete()
	return bool(deleted)


def send_survey_again(survey_id: str) -> dict | None:
	survey = Survey.objects.filter(id=survey_id).first()
	if not survey:
		return None

	survey.last_sent = date.today()
	survey.save(update_fields=["last_sent"])

	return {
		"sent": True,
		"id": survey.id,
		"question": survey.question,
		"lastSent": survey.last_sent.isoformat(),
	}
