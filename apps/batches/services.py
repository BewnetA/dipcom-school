from __future__ import annotations

from datetime import date
import re
from uuid import uuid4

from django.db.models import Q
from django.utils import timezone

from .models import Batch, Timeslot
from .serializers import serialize_batch, serialize_batches
from .lifecycle import sync_completed_batch_students
from apps.students.models import Student


def _extract_numeric_name(value: str) -> int | None:
	match = re.fullmatch(r"\s*(\d{1,6})\s*", value or "")
	if not match:
		return None
	return int(match.group(1))


def get_next_batch_name() -> str:
	max_value = 0
	for name in Batch.objects.values_list("name", flat=True):
		numeric = _extract_numeric_name(str(name))
		if numeric is not None:
			max_value = max(max_value, numeric)

	return f"{max_value + 1:03d}"


def _to_iso_date(value) -> str:
	if hasattr(value, "isoformat"):
		return value.isoformat()
	return str(value)


def _batch_to_dict(batch: Batch) -> dict:
	return {
		"id": batch.id,
		"name": batch.name,
		"startDate": _to_iso_date(batch.start_date),
		"endDate": _to_iso_date(batch.end_date),
		"registrationEndDate": _to_iso_date(batch.registration_end_date) if batch.registration_end_date else None,
		"capacity": batch.capacity,
		"timeslot1Capacity": batch.timeslot_1_capacity,
		"timeslot2Capacity": batch.timeslot_2_capacity,
		"timeslot3Capacity": batch.timeslot_3_capacity,
		"timeslot4Capacity": batch.timeslot_4_capacity,
		"timeslot5Capacity": batch.timeslot_5_capacity,
		"extensionCapacity": batch.extension_capacity,
		"computerCoursePayment": float(batch.computer_course_payment) if batch.computer_course_payment else None,
		"officeCoursePayment": float(batch.office_course_payment) if batch.office_course_payment else None,
		"computerCoursePaymentMWF": float(batch.computer_course_payment_mwf) if batch.computer_course_payment_mwf else None,
		"computerCoursePaymentTTS": float(batch.computer_course_payment_tts) if batch.computer_course_payment_tts else None,
		"computerCoursePaymentExtension": float(batch.computer_course_payment_extension) if batch.computer_course_payment_extension else None,
		"officeCoursePaymentMWF": float(batch.office_course_payment_mwf) if batch.office_course_payment_mwf else None,
		"officeCoursePaymentTTS": float(batch.office_course_payment_tts) if batch.office_course_payment_tts else None,
		"officeCoursePaymentExtension": float(batch.office_course_payment_extension) if batch.office_course_payment_extension else None,
		"status": batch.status,
		"createdAt": batch.created_at.isoformat() if getattr(batch, "created_at", None) else None,
	}


def list_timeslots() -> list[dict]:
	return [
		{"id": str(item.id), "label": item.label, "position": item.position}
		for item in Timeslot.objects.filter(is_active=True).order_by("position", "id")
	]


def _canonical_timeslot_label(label: str | None) -> str:
	value = str(label or "").strip()
	if not value:
		return ""
	# Strip display suffixes like "(Morning)" and normalize aliases.
	base = value.split("(", 1)[0].strip()
	lower = base.lower()
	if "night" in lower:
		return "Night class"
	if base.startswith("3:00 - 4:30"):
		return "3:00 - 4:30"
	if base.startswith("4:30 - 6:00"):
		return "4:30 - 6:00"
	if base.startswith("8:00 - 9:30"):
		return "8:00 - 9:30"
	if base.startswith("9:30 - 11:00"):
		return "9:30 - 11:00"
	return base


def get_available_timeslots(batch_id: str, day_choice: str = "MWF") -> list[dict]:
	"""Get available timeslots for a given batch and day choice."""
	batch = Batch.objects.filter(id=batch_id).first()
	if not batch:
		return []

	available: list[dict] = []
	for slot in list_timeslots():
		if _check_timeslot_available(batch, slot["label"], day_choice):
			available.append(slot)
	return available


def _get_timeslot_count(batch_id: str, timeslot_label: str, day_choice: str) -> int:
	"""Get number of students registered for a specific timeslot and day choice."""
	students = Student.objects.filter(
		batch_id=batch_id,
		status__in=["pending", "approved"],
	)
	target_label = _canonical_timeslot_label(timeslot_label)
	count = 0
	for student in students:
		meta = student.meta or {}
		student_label = _canonical_timeslot_label(meta.get("preferredTime"))
		if student_label == target_label and meta.get("dayChoice") == day_choice:
			count += 1
	return count


def _get_extension_count(batch_id: str) -> int:
	"""Get number of students registered for extension."""
	students = Student.objects.filter(
		batch_id=batch_id,
		status__in=["pending", "approved"],
	)
	count = 0
	for student in students:
		meta = student.meta or {}
		if meta.get("dayChoice") == "Extension":
			count += 1
	return count


def _check_timeslot_available(batch: Batch, timeslot_label: str, day_choice: str) -> bool:
	"""Check if a timeslot has capacity for a given day choice."""
	if day_choice == "Extension":
		# Extension students use extension_capacity
		# If no capacity is set (None), treat as available
		if batch.extension_capacity is None:
			return True
		if batch.extension_capacity <= 0:
			return False
		current = _get_extension_count(batch.id)
		return current < batch.extension_capacity
	
	# Determine which timeslot capacity to check
	capacity_map = {
		"3:00 - 4:30": batch.timeslot_1_capacity,
		"4:30 - 6:00": batch.timeslot_2_capacity,
		"8:00 - 9:30": batch.timeslot_3_capacity,
		"9:30 - 11:00": batch.timeslot_4_capacity,
		"Night class": batch.timeslot_5_capacity,
	}

	canonical_label = _canonical_timeslot_label(timeslot_label)
	capacity = capacity_map.get(canonical_label)
	# If capacity is not set (None), treat as available
	if capacity is None:
		return True
	# If capacity is 0 or negative, not available
	if capacity <= 0:
		return False
	
	# For MWF/TTS, each can have up to capacity students
	current = _get_timeslot_count(batch.id, canonical_label, day_choice)
	return current < capacity


def _is_batch_full(batch: Batch) -> bool:
	"""Check if all timeslots and extension are at capacity."""
	# If overall batch capacity is explicitly set, enforce it as a hard cap.
	# Treat None as unlimited (available), and 0 or negative as no capacity (full).
	if batch.capacity is not None:
		if batch.capacity <= 0:
			return True
		total_registered = Student.objects.filter(batch_id=batch.id).exclude(status="rejected").count()
		if total_registered >= batch.capacity:
			return True
	
	# For simplicity: batch is full if all day-timeslot combinations are at capacity
	# Check if we can find any available slot
	timeslot_labels = ["3:00 - 4:30", "4:30 - 6:00", "8:00 - 9:30", "9:30 - 11:00", "Night class"]
	
	has_available_slot = False
	for ts_label in timeslot_labels:
		for day in ["MWF", "TTS"]:
			if _check_timeslot_available(batch, ts_label, day):
				has_available_slot = True
				break
		if has_available_slot:
			break
	
	# Also check extension capacity. None => available, 0/neg => not available.
	if not has_available_slot:
		if batch.extension_capacity is None:
			has_available_slot = True
		elif batch.extension_capacity > 0:
			if _get_extension_count(batch.id) < batch.extension_capacity:
				has_available_slot = True
	
	return not has_available_slot


def close_full_batches() -> None:
	"""Close batches that are completely full or past registration end date.
	Also auto-complete batches when end_date passes and graduate students."""
	today = timezone.localdate()
	
	# Auto-complete batches past their end_date and graduate students
	batches_to_complete = Batch.objects.filter(
		end_date__lt=today,
		status__in=['open', 'closed']
	)
	for batch in batches_to_complete:
		batch.status = 'completed'
		batch.save(update_fields=['status', 'updated_at'])
		# Bulk graduate students (excluding dropouts)
		Student.objects.filter(batch_id=batch.id, status='approved').exclude(
			graduation_status='dropout'
		).update(graduation_status='graduated', graduated=True)
	
	# Close batches past registration end date
	Batch.objects.filter(
		registration_end_date__lt=today,
		status__in=['open']
	).update(status='closed')
	
	# Close batches that are full
	open_batches = Batch.objects.filter(status='open')
	for batch in open_batches:
		if _is_batch_full(batch):
			batch.status = 'closed'
			batch.save()


def complete_batch(batch_id: str) -> dict | None:
	"""Mark batch as completed and graduate all students in the batch."""
	batch = Batch.objects.filter(id=batch_id).first()
	if not batch:
		return None
	
	# Mark batch as completed
	batch.status = 'completed'
	batch.save(update_fields=['status', 'updated_at'])
	
	# Bulk update all students in batch to graduated, but exclude dropouts
	Student.objects.filter(batch_id=batch_id, status='approved').exclude(graduation_status='dropout').update(
		graduation_status='graduated',
		graduated=True,
	)
	
	return _batch_to_dict(batch)


def _batch_students(batch_id: str) -> list[dict]:
	# Only include students who have been approved for the batch
	items = Student.objects.filter(batch_id=batch_id, status="approved").values(
		"id",
		"name",
		"phone",
		"batch_id",
		"payment_status",
		"tuition_fee",
		"amount_paid",
		"grade",
		"employment_status",
	)
	return [
		{
			"id": item["id"],
			"name": item["name"],
			"phone": item["phone"],
			"batchId": item["batch_id"] or "",
			"paymentStatus": item["payment_status"],
			"tuitionFee": int(item["tuition_fee"]),
			"amountPaid": int(item["amount_paid"]),
			"grade": item["grade"],
			"employmentStatus": item["employment_status"],
			"dayChoice": (item["meta"].get("dayChoice") if isinstance(item.get("meta"), dict) else None),
			"preferredTime": (item["meta"].get("preferredTime") if isinstance(item.get("meta"), dict) else None),
		}
		for item in items
	]


def _compute_batch_metrics(batch: dict) -> dict:
	students = _batch_students(batch["id"])
	graded = [student for student in students if student.get("grade") is not None]
	employed = len([student for student in students if student.get("employmentStatus") == "yes"])
	avg_grade = round(sum(student["grade"] for student in graded) / len(graded)) if graded else 0
	employment_rate = round((employed / len(students)) * 100) if students else 0

	# Keep canonical lifecycle status from DB: open | closed | completed.
	status = (batch.get("status") or "open").strip().lower()
	if status not in {"open", "closed", "completed"}:
		status = "open"

	return {
		**batch,
		"status": status,
		"studentCount": len(students),
		"avgGrade": avg_grade,
		"employmentRate": employment_rate,
	}


def list_batches(active_only: bool = False) -> list[dict]:
	sync_completed_batch_students()
	close_full_batches()  # Auto-close batches that are full or past registration end
	queryset = Batch.objects.all()
	
	# Always exclude closed batches from registration lists
	if active_only:
		queryset = queryset.filter(status='open')
		today = timezone.localdate()
		# Include batches where registration_end_date is null (interpreted as still open)
		queryset = queryset.filter(Q(registration_end_date__isnull=True) | Q(registration_end_date__gte=today))
		queryset = queryset.order_by("-registration_end_date", "-start_date", "-created_at")
	else:
		queryset = queryset.order_by("-created_at", "-id")
	
	items = [_compute_batch_metrics(_batch_to_dict(batch)) for batch in queryset]
	return serialize_batches(items)


def _validate_batch_dates(start_date: date, end_date: date, registration_end_date: date) -> None:
	if start_date > end_date:
		raise ValueError("Start date cannot be after end date.")
	if registration_end_date > end_date:
		raise ValueError("Registration end date cannot be after batch end date.")


def get_batch_by_id(batch_id: str, student_search: str | None = None) -> dict | None:
	sync_completed_batch_students()
	batch = Batch.objects.filter(id=batch_id).first()
	if not batch:
		return None

	# Only surface approved students in the batch listing
	queryset = Student.objects.filter(batch_id=batch_id, status="approved")
	query = (student_search or "").strip()
	if query:
		normalized_query = query.replace(" ", "")
		queryset = queryset.filter(Q(name__icontains=query) | Q(phone__icontains=normalized_query))

	students = [
		{
			"id": item["id"],
			"name": item["name"],
			"phone": item["phone"],
			"batchId": item["batch_id"] or "",
			"paymentStatus": item["payment_status"],
			"tuitionFee": int(item["tuition_fee"]),
			"amountPaid": int(item["amount_paid"]),
			"grade": item["grade"],
			"employmentStatus": item["employment_status"],
			"dayChoice": (item["meta"].get("dayChoice") if isinstance(item.get("meta"), dict) else None),
			"preferredTime": (item["meta"].get("preferredTime") if isinstance(item.get("meta"), dict) else None),
		}
		for item in queryset.values(
			"id",
			"name",
			"phone",
			"batch_id",
			"payment_status",
			"tuition_fee",
			"amount_paid",
			"grade",
			"employment_status",
			"meta",
		)
	]

	detail = {
		**_compute_batch_metrics(_batch_to_dict(batch)),
		"students": students,
	}
	return serialize_batch(detail)


def create_batch(payload: dict) -> dict:
	name = str(payload.get("name", "")).strip()
	if not name:
		raise ValueError("Batch name is required.")
	if Batch.objects.filter(name__iexact=name).exists():
		raise ValueError("A batch with this name already exists.")

	start_date = payload.get("startDate")
	end_date = payload.get("endDate")
	registration_end_date = payload.get("registrationEndDate")
	if not start_date or not end_date or not registration_end_date:
		raise ValueError("Start date, end date, and registration end date are required.")

	start_date_obj = date.fromisoformat(str(start_date))
	end_date_obj = date.fromisoformat(str(end_date))
	registration_end_date_obj = date.fromisoformat(str(registration_end_date))
	_validate_batch_dates(start_date_obj, end_date_obj, registration_end_date_obj)

	today = timezone.localtime()
	if registration_end_date_obj >= today.date() and Batch.objects.filter(registration_end_date__isnull=False, registration_end_date__gte=today.date()).exists():
		raise ValueError("There is already an enrollable batch. Close it before creating another.")

	batch_id = payload.get("id") or f"b-{uuid4().hex[:8]}"
	while Batch.objects.filter(id=batch_id).exists():
		batch_id = f"b-{uuid4().hex[:8]}"

	batch = Batch.objects.create(
		id=batch_id,
		name=name,
		start_date=start_date_obj,
		end_date=end_date_obj,
		registration_end_date=registration_end_date_obj,
		capacity=payload.get("capacity"),
		timeslot_1_capacity=payload.get("timeslot1Capacity"),
		timeslot_2_capacity=payload.get("timeslot2Capacity"),
		timeslot_3_capacity=payload.get("timeslot3Capacity"),
		timeslot_4_capacity=payload.get("timeslot4Capacity"),
		timeslot_5_capacity=payload.get("timeslot5Capacity"),
		extension_capacity=payload.get("extensionCapacity"),
		computer_course_payment=payload.get("computerCoursePayment"),
		office_course_payment=payload.get("officeCoursePayment"),
		computer_course_payment_mwf=payload.get("computerCoursePaymentMWF"),
		computer_course_payment_tts=payload.get("computerCoursePaymentTTS"),
		computer_course_payment_extension=payload.get("computerCoursePaymentExtension"),
		office_course_payment_mwf=payload.get("officeCoursePaymentMWF"),
		office_course_payment_tts=payload.get("officeCoursePaymentTTS"),
		office_course_payment_extension=payload.get("officeCoursePaymentExtension"),
	)
	return serialize_batch(_compute_batch_metrics(_batch_to_dict(batch)))


def update_batch(batch_id: str, payload: dict) -> dict | None:
	batch = Batch.objects.filter(id=batch_id).first()
	if not batch:
		return None

	if "name" in payload:
		name = str(payload["name"]).strip()
		if not name:
			raise ValueError("Batch name is required.")
		if Batch.objects.filter(name__iexact=name).exclude(id=batch_id).exists():
			raise ValueError("A batch with this name already exists.")
		batch.name = name
	if "startDate" in payload:
		batch.start_date = date.fromisoformat(str(payload["startDate"]))
	if "endDate" in payload:
		batch.end_date = date.fromisoformat(str(payload["endDate"]))
	if "registrationEndDate" in payload:
		batch.registration_end_date = date.fromisoformat(str(payload["registrationEndDate"]))
	if "capacity" in payload:
		batch.capacity = payload["capacity"]
	if "timeslot1Capacity" in payload:
		batch.timeslot_1_capacity = payload["timeslot1Capacity"]
	if "timeslot2Capacity" in payload:
		batch.timeslot_2_capacity = payload["timeslot2Capacity"]
	if "timeslot3Capacity" in payload:
		batch.timeslot_3_capacity = payload["timeslot3Capacity"]
	if "timeslot4Capacity" in payload:
		batch.timeslot_4_capacity = payload["timeslot4Capacity"]
	if "timeslot5Capacity" in payload:
		batch.timeslot_5_capacity = payload["timeslot5Capacity"]
	if "extensionCapacity" in payload:
		batch.extension_capacity = payload["extensionCapacity"]
	if "computerCoursePayment" in payload:
		batch.computer_course_payment = payload["computerCoursePayment"]
	if "officeCoursePayment" in payload:
		batch.office_course_payment = payload["officeCoursePayment"]
	if "computerCoursePaymentMWF" in payload:
		batch.computer_course_payment_mwf = payload["computerCoursePaymentMWF"]
	if "computerCoursePaymentTTS" in payload:
		batch.computer_course_payment_tts = payload["computerCoursePaymentTTS"]
	if "computerCoursePaymentExtension" in payload:
		batch.computer_course_payment_extension = payload["computerCoursePaymentExtension"]
	if "officeCoursePaymentMWF" in payload:
		batch.office_course_payment_mwf = payload["officeCoursePaymentMWF"]
	if "officeCoursePaymentTTS" in payload:
		batch.office_course_payment_tts = payload["officeCoursePaymentTTS"]
	if "officeCoursePaymentExtension" in payload:
		batch.office_course_payment_extension = payload["officeCoursePaymentExtension"]

	if batch.start_date and batch.end_date and batch.registration_end_date:
		_validate_batch_dates(batch.start_date, batch.end_date, batch.registration_end_date)

	batch.save()
	return serialize_batch(_compute_batch_metrics(_batch_to_dict(batch)))


def delete_batch(batch_id: str) -> bool:
	deleted, _ = Batch.objects.filter(id=batch_id).delete()
	return bool(deleted)
