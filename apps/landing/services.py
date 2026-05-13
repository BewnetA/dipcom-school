from __future__ import annotations

from uuid import uuid4

from apps.batches.models import Batch
from apps.students.models import Student

from .dummy_data import LANDING_CONTENT
from .models import LandingRegistration
from .serializers import (
    serialize_landing_content,
    serialize_registration,
    serialize_registrations,
)
from apps.students.services import create_student as create_student_record


def _normalize_phone(phone: str) -> str:
	return "".join(ch for ch in str(phone or "") if ch.isdigit())


def _phone_exists_anywhere(phone: str) -> bool:
	normalized = _normalize_phone(phone)
	if not normalized:
		return False

	for existing in LandingRegistration.objects.only("phone").iterator():
		if _normalize_phone(existing.phone) == normalized:
			return True

	for existing in Student.objects.only("phone").iterator():
		if _normalize_phone(existing.phone) == normalized:
			return True

	return False


def _registration_to_dict(item: LandingRegistration) -> dict:
	return {
		"id": item.id,
		"name": item.name,
		"phone": item.phone,
		"batchId": item.batch_id or "",
		"registrationType": item.registration_type,
		"learningTime": item.learning_time,
		"createdAt": item.created_at.replace(microsecond=0).isoformat(),
	}


def get_landing_content() -> dict:
	return serialize_landing_content(LANDING_CONTENT)


def list_registrations() -> list[dict]:
	items = [_registration_to_dict(item) for item in LandingRegistration.objects.select_related("batch").all()]
	return serialize_registrations(items)


def create_registration(payload: dict) -> dict:
	phone = str(payload.get("phone", "")).strip()
	if _phone_exists_anywhere(phone):
		raise ValueError("Phone number is already registered")

	day_choice = str(payload.get("dayChoice", "")).strip()
	if day_choice not in {"MWF", "TTS", "Extension"}:
		raise ValueError("Day choice is required (MWF, TTS, or Extension)")

	preferred_time = str(payload.get("preferredTime", "")).strip()
	if day_choice != "Extension" and not preferred_time:
		raise ValueError("Preferred time is required for MWF/TTS students")

	registration_type = payload.get("registrationType", "online")
	if registration_type == "online" and not payload.get("paymentScreenshot"):
		raise ValueError("Payment screenshot is required for online registration")

	registration_id = payload.get("id") or f"reg-{uuid4().hex[:8]}"
	while LandingRegistration.objects.filter(id=registration_id).exists():
		registration_id = f"reg-{uuid4().hex[:8]}"

	batch_id = payload.get("batchId")
	batch = Batch.objects.filter(id=batch_id).first() if batch_id else None
	# First attempt to create the Student record so any validation errors
	# (capacity, closed batch, etc.) are surfaced to the caller and the
	# landing registration is not created when the batch cannot accept more
	# students. Let exceptions propagate as ValueError so the view returns
	# a 400 with a meaningful message.
	created_student = create_student_record(payload)

	registration = LandingRegistration.objects.create(
		id=registration_id,
		name=payload.get("name", ""),
		phone=phone,
		batch=batch,
		registration_type=registration_type,
		learning_time=preferred_time or payload.get("learningTime", "morning"),
		meta=payload,
	)

	return serialize_registration(_registration_to_dict(registration))
