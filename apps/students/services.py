from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from django.db.models import Q
from django.utils import timezone

from apps.batches.models import Batch
from apps.batches.lifecycle import sync_completed_batch_students
from apps.common.services import get_course_fees
from apps.surveys.models import Survey
from .models import EmploymentCheckin, Student
from .serializers import serialize_student, serialize_students, serialize_students_summary


def _normalize_phone(phone: str) -> str:
	return "".join(ch for ch in str(phone or "") if ch.isdigit())


def _phone_exists(phone: str, exclude_student_id: str | None = None) -> bool:
	normalized = _normalize_phone(phone)
	if not normalized:
		return False

	queryset = Student.objects.only("id", "phone")
	if exclude_student_id:
		queryset = queryset.exclude(id=exclude_student_id)

	for existing in queryset.iterator():
		if _normalize_phone(existing.phone) == normalized:
			return True

	return False


def _meta_dict(student: Student) -> dict:
	return student.meta if hasattr(student, "meta") and isinstance(student.meta, dict) else {}


def _value_exists(value: object) -> bool:
	return value not in (None, "", [])


def _batch_shift_payment(batch: Batch | None, course: str, day_choice: str | None) -> int | None:
	if not batch:
		return None

	suffix_map = {
		"mwf": "mwf",
		"tts": "tts",
		"extension": "extension",
	}
	suffix = suffix_map.get(str(day_choice or "").strip().lower())
	if not suffix:
		return None

	field_name = f"{course}_course_payment_{suffix}"
	value = getattr(batch, field_name, None)
	if value not in (None, ""):
		return int(value)

	legacy_value = getattr(batch, f"{course}_course_payment", None)
	if legacy_value not in (None, ""):
		return int(legacy_value)

	return None


def _calculate_tuition(batch: Batch | None, courses: dict, day_choice: str | None) -> int:
	course_fees = get_course_fees()
	total = 0
	for course in ("computer", "office"):
		if isinstance(courses, dict) and courses.get(course):
			batch_price = _batch_shift_payment(batch, course, day_choice)
			if batch_price is None:
				batch_price = int(course_fees[course])
			total += int(batch_price)
	return total


def _registration_completion_missing_fields(student: Student) -> list[str]:
	meta = _meta_dict(student)
	missing: list[str] = []

	if not _value_exists(meta.get("sex")):
		missing.append("Sex")
	if not _value_exists(meta.get("dob")):
		missing.append("Date of Birth")
	if not _value_exists(meta.get("nationality")):
		missing.append("Nationality")
	if not _value_exists(meta.get("city")):
		missing.append("City")
	if not _value_exists(meta.get("subCity")):
		missing.append("Sub-City")
	if not _value_exists(meta.get("kebele")):
		missing.append("Kebele")
	if not _value_exists(meta.get("houseNo")):
		missing.append("House No.")
	if not _value_exists(meta.get("maritalStatus")):
		missing.append("Marital Status")

	emergency = meta.get("emergency") if isinstance(meta.get("emergency"), dict) else {}
	if not _value_exists(emergency.get("name")):
		missing.append("Emergency Contact Name")
	if not _value_exists(emergency.get("relationship")):
		missing.append("Emergency Relationship")
	if not _value_exists(emergency.get("subCity")):
		missing.append("Emergency Sub-City")
	if not _value_exists(emergency.get("kebele")):
		missing.append("Emergency Kebele")
	if not _value_exists(emergency.get("houseNo")):
		missing.append("Emergency House No.")
	if not _value_exists(emergency.get("mobile")):
		missing.append("Emergency Mobile")

	education = meta.get("education") if isinstance(meta.get("education"), dict) else {}
	if not _value_exists(education.get("level")):
		missing.append("Education Level")
	if not _value_exists(meta.get("dayChoice")):
		missing.append("Day Choice")
	elif meta.get("dayChoice") != "Extension" and not _value_exists(meta.get("preferredTime")):
		missing.append("Preferred Time")

	courses = meta.get("courses") if isinstance(meta.get("courses"), dict) else {}
	has_course = any(bool(value) for value in courses.values())
	if not has_course:
		missing.append("Course Selection")

	return missing


def _is_completion_needed(student: Student) -> bool:
	if getattr(student, "registration_type", None) != "bot":
		return False
	if getattr(student, "status", None) != "approved":
		return False
	return bool(_registration_completion_missing_fields(student))


def _latest_followup_checkin(student: Student) -> EmploymentCheckin | None:
	return (
		EmploymentCheckin.objects.select_related("survey")
		.filter(student_id=student.id)
		.order_by("-checked_at", "-id")
		.first()
	)


def _followup_summary() -> dict:
	survey = Survey.objects.filter(id="job_followup").first()
	if not survey:
		return {
			"id": "job_followup",
			"question": "Have you found a job after graduation? Please answer Yes or No.",
			"lastSent": None,
			"responses": {"yes": 0, "no": 0},
		}

	return {
		"id": survey.id,
		"question": survey.question,
		"lastSent": survey.last_sent.isoformat() if survey.last_sent else None,
		"responses": {"yes": int(survey.response_yes), "no": int(survey.response_no)},
	}


def _student_to_dict(student: Student) -> dict:
	meta = _meta_dict(student)
	sex = meta.get("sex") if meta else None
	if not sex and hasattr(student, "sex"):
		sex = getattr(student, "sex", None)
	completion_missing_fields = _registration_completion_missing_fields(student)
	needs_completion = _is_completion_needed(student)
	followup_checkin = _latest_followup_checkin(student)
	followup_response = None
	followup_checked_at = None
	followup_survey_id = None
	followup_question = None
	if followup_checkin:
		followup_response = "yes" if followup_checkin.is_employed else "no"
		followup_checked_at = followup_checkin.checked_at.isoformat() if followup_checkin.checked_at else None
		followup_survey_id = followup_checkin.survey_id
		followup_question = followup_checkin.survey.question if getattr(followup_checkin, "survey", None) else None
	return {
		"id": student.id,
		"name": student.name,
		"phone": student.phone,
		"fatherName": student.father_name,
		"telegramUserId": student.telegram_user_id,
		"telegramUsername": student.telegram_username,
		"sex": sex,
		"batchId": student.batch_id or "",
		"paymentStatus": student.payment_status,
		"tuitionFee": int(student.tuition_fee),
		# If a record is marked as paid but `amount_paid` is zero (legacy/landing cases),
		# treat it as fully paid so analytics match the students UI where paid implies no due.
		"amountPaid": (
			int(student.amount_paid)
			if int(student.amount_paid) > 0
			else int(student.tuition_fee)
		) if student.payment_status == "paid" else int(student.amount_paid),
		"graduated": bool(getattr(student, "graduated", False)),
		"graduationStatus": getattr(student, "graduation_status", None) or (
			"graduated" if bool(getattr(student, "graduated", False)) or (student.grade is not None) else "not_graduated"
		),
		"grade": student.grade,
		"employmentStatus": student.employment_status,
		"registrationType": student.registration_type,
		"dayChoice": (meta.get("dayChoice") if isinstance(meta, dict) else None),
		"preferredTime": (meta.get("preferredTime") if isinstance(meta, dict) else None),
		"status": getattr(student, "status", "pending"),
		"rejectedAt": student.rejected_at.isoformat() if getattr(student, "rejected_at", None) else None,
		"registrationDate": student.registration_date.isoformat() if student.registration_date else None,
		"createdAt": student.created_at.isoformat() if getattr(student, "created_at", None) else None,
		"meta": student.meta if hasattr(student, "meta") and student.meta else {},
		"needsCompletion": needs_completion,
		"completionMissingFields": completion_missing_fields if needs_completion else [],
		"followUpResponse": followup_response,
		"followUpCheckedAt": followup_checked_at,
		"followUpSurveyId": followup_survey_id,
		"followUpQuestion": followup_question,
	}


def _apply_filters(filters: dict) -> list[Student]:
	sync_completed_batch_students()
	queryset = Student.objects.select_related("batch").all()

	search = (filters.get("search") or "").strip()
	if search:
		queryset = queryset.filter(Q(name__icontains=search) | Q(phone__icontains=search))

	batch_id = (filters.get("batchId") or "").strip()
	if batch_id:
		queryset = queryset.filter(batch_id=batch_id)

	payment_status = (filters.get("paymentStatus") or "").strip()
	if payment_status:
		queryset = queryset.filter(payment_status=payment_status)

	# allow filtering by registration type (online / in_person)
	registration_type = (filters.get("registrationType") or "").strip()
	if registration_type:
		queryset = queryset.filter(registration_type=registration_type)

	# allow filtering by status (pending / approved / rejected)
	status = (filters.get("status") or "").strip()
	if status:
		queryset = queryset.filter(status=status)

	employment_status = (filters.get("employmentStatus") or "").strip()
	if employment_status:
		queryset = queryset.filter(employment_status=employment_status)

	grade_band = filters.get("gradeBand")
	if grade_band == "na":
		queryset = queryset.filter(grade__isnull=True)
	elif grade_band == "a":
		queryset = queryset.filter(grade__gte=85)
	elif grade_band == "b":
		queryset = queryset.filter(grade__gte=70, grade__lt=85)
	elif grade_band == "c":
		queryset = queryset.filter(grade__lt=70, grade__isnull=False)

	graduated = filters.get("graduated")
	# support new graduation_status field if present on model
	_has_status_field = any(f.name == 'graduation_status' for f in Student._meta.get_fields())
	if _has_status_field:
		if graduated in ("graduated", "not_graduated", "dropout"):
			queryset = queryset.filter(graduation_status=graduated)
	else:
		if graduated == "graduated":
			queryset = queryset.filter(graduated=True)
		elif graduated == "not_graduated":
			queryset = queryset.filter(graduated=False)

	return list(queryset)


def list_students(filters: dict | None = None) -> list[dict]:
	filters = filters or {}
	items = [_student_to_dict(student) for student in _apply_filters(filters)]
	return serialize_students(items)


def list_approval_students(search: str | None = None) -> list[dict]:
	queryset = Student.objects.select_related("batch").filter(registration_type="online", status="pending")
	term = (search or "").strip()
	if term:
		queryset = queryset.filter(Q(name__icontains=term) | Q(phone__icontains=term))
	items = sorted(
		[_student_to_dict(student) for student in queryset],
		key=lambda item: item.get("registrationDate") or "",
	)
	return serialize_students(items)


def get_students_summary(filters: dict | None = None) -> dict:
	filters = filters or {}
	items = [_student_to_dict(student) for student in _apply_filters(filters)]
	return serialize_students_summary(items)


def get_student_by_id(student_id: str) -> dict | None:
	student = Student.objects.filter(id=student_id).first()
	if not student:
		return None
	return serialize_student(_student_to_dict(student))


def create_student(payload: dict) -> dict:
	# Defensive validation: ensure required registration fields are present.
	def _get(path, default=None):
		parts = path.split('.')
		cur = payload
		for p in parts:
			if not isinstance(cur, dict):
				return default
			cur = cur.get(p)
		return cur if cur is not None and cur != "" else default

	missing: list[str] = []
	# simple required fields
	for label, key in (
		("Name", "name"),
		("Phone", "phone"),
		("Batch", "batchId"),
		("Sex", "sex"),
		("Date of Birth", "dob"),
		("Nationality", "nationality"),
		("City", "city"),
		("Sub-City", "subCity"),
		("Kebele", "kebele"),
		("House No.", "houseNo"),
		("Marital Status", "maritalStatus"),
		("Education Level", "education.level"),
	):
		if _get(key) is None:
			missing.append(label)

	# emergency fields (nested)
	for label, key in (
		("Emergency Name", "emergency.name"),
		("Emergency Relationship", "emergency.relationship"),
		("Emergency Sub-City", "emergency.subCity"),
		("Emergency Kebele", "emergency.kebele"),
		("Emergency House No.", "emergency.houseNo"),
		("Emergency Mobile", "emergency.mobile"),
	):
		if _get(key) is None:
			missing.append(label)

	day_choice = _get("dayChoice")
	if day_choice is None:
		missing.append("Day Choice")
	elif day_choice not in ("MWF", "TTS", "Extension"):
		raise ValueError("Day Choice must be one of MWF, TTS, or Extension")

	preferred_time = _get("preferredTime")
	if day_choice in ("MWF", "TTS") and preferred_time is None:
		missing.append("Preferred Time")

	# courses: expect payload.courses with at least one truthy
	courses = payload.get("courses")
	has_course = False
	if isinstance(courses, dict):
		for v in courses.values():
			if v:
				has_course = True
				break
	if not has_course:
		missing.append("Course selection")

	# paymentStatus required for in-person registrations
	reg_type = payload.get("registrationType") or payload.get("registration_type") or "online"
	if reg_type == "in_person":
		if _get("paymentStatus") is None and _get("payment_status") is None:
			missing.append("Payment Status")

	if missing:
		raise ValueError("Missing required fields: " + ", ".join(missing))

	phone = str(payload.get("phone", "")).strip()
	if _phone_exists(phone):
		raise ValueError("Phone number is already registered")

	student_id = payload.get("id") or f"s-{uuid4().hex[:8]}"
	while Student.objects.filter(id=student_id).exists():
		student_id = f"s-{uuid4().hex[:8]}"

	grade = payload.get("grade")
	if grade == "":
		grade = None

	batch_id = payload.get("batchId")
	batch = Batch.objects.filter(id=batch_id).first() if batch_id else None

	# Allow registration only when batch lifecycle status is open.
	if batch and batch.status != 'open':
		raise ValueError("This batch is not accepting registrations")

	# Validate timeslot capacity
	if batch:
		from apps.batches.services import _check_timeslot_available
		day_choice = payload.get("dayChoice")
		preferred_time = payload.get("preferredTime")
		
		if day_choice in ("MWF", "TTS"):
			if not preferred_time:
				raise ValueError("Preferred time is required for MWF/TTS registration")
			if not _check_timeslot_available(batch, preferred_time, day_choice):
				raise ValueError(f"The {preferred_time} timeslot for {day_choice} is full. Please select another option.")
		elif day_choice == "Extension":
			if not _check_timeslot_available(batch, "Extension", "Extension"):
				raise ValueError("The Extension timeslot is full. Please select another option.")

	# determine default payment status: prefer explicit payload; for online
	# registrations assume payment is provided (landing registrations are paid)
	_default_payment = None
	if "paymentStatus" in payload and payload.get("paymentStatus") is not None:
		_default_payment = payload.get("paymentStatus")
	else:
		if payload.get("registrationType", "online") == "online":
			_default_payment = "paid"
		else:
			_default_payment = "not_paid"

	# compute tuition so we can default amount_paid appropriately
	if "tuitionFee" in payload and payload.get("tuitionFee") is not None:
		_tuition = int(payload["tuitionFee"])
	else:
		courses = payload.get("courses") or {}
		_tuition = _calculate_tuition(batch, courses if isinstance(courses, dict) else {}, payload.get("dayChoice"))
	_default_amount_paid = payload.get("amountPaid")
	if _default_amount_paid is None:
		if _default_payment == "paid":
			_default_amount_paid = _tuition
		elif _default_payment == "partial":
			_default_amount_paid = round(_tuition * 0.5)
		else:
			_default_amount_paid = 0

	create_kwargs = {
		"id": student_id,
		"name": payload.get("name", ""),
		"phone": phone,
		"batch": batch,
		"payment_status": _default_payment,
		"tuition_fee": _tuition,
		"amount_paid": int(_default_amount_paid),
		# set both legacy boolean and new graduation_status if provided
		"graduated": bool(payload.get("graduated", False)),
		"graduation_status": (
			(payload.get("graduationStatus") or payload.get("graduation_status"))
			if payload.get("graduationStatus") or payload.get("graduation_status") is not None
			else ("graduated" if bool(payload.get("graduated", False)) or grade is not None else "not_graduated")
		),
		"grade": grade,
		"employment_status": payload.get("employmentStatus", "no"),
		"registration_type": payload.get("registrationType", "online"),
		# set status based on registration type: in_person -> approved, online/bot -> pending
		"status": "approved" if payload.get("registrationType", "online") == "in_person" else "pending",
		"meta": payload or {},
	}
	if payload.get("registrationDate"):
		create_kwargs["registration_date"] = payload["registrationDate"]

	student = Student.objects.create(
		**create_kwargs,
	)

	if batch:
		from apps.batches.services import _is_batch_full
		if _is_batch_full(batch):
			batch.status = 'closed'
			batch.save(update_fields=["status", "updated_at"])

	return serialize_student(_student_to_dict(student))


def update_student(student_id: str, payload: dict) -> dict | None:
	student = Student.objects.filter(id=student_id).first()
	if not student:
		return None

	if "name" in payload:
		student.name = payload["name"]
	if "phone" in payload:
		phone = str(payload["phone"] or "").strip()
		if _phone_exists(phone, exclude_student_id=student_id):
			raise ValueError("Phone number is already registered")
		student.phone = phone
	if "batchId" in payload:
		batch_id = payload.get("batchId")
		student.batch = Batch.objects.filter(id=batch_id).first() if batch_id else None
	if "paymentStatus" in payload:
		student.payment_status = payload["paymentStatus"]
	if "tuitionFee" in payload:
		student.tuition_fee = int(payload["tuitionFee"])
	if "amountPaid" in payload:
		student.amount_paid = int(payload["amountPaid"])
	if "graduated" in payload:
		student.graduated = bool(payload["graduated"])
	if "graduationStatus" in payload or "graduation_status" in payload:
		new_status = payload.get("graduationStatus") or payload.get("graduation_status")
		if new_status in ("graduated", "not_graduated", "dropout"):
			student.graduation_status = new_status
			# keep legacy boolean roughly in sync
			student.graduated = True if new_status == "graduated" else False
	if "grade" in payload:
		student.grade = None if payload["grade"] == "" else payload["grade"]
	if "employmentStatus" in payload:
		student.employment_status = payload["employmentStatus"]
	if "registrationType" in payload:
		student.registration_type = payload["registrationType"]
	if "status" in payload:
		student.status = payload["status"]
		if student.status == "rejected" and not student.rejected_at:
			student.rejected_at = timezone.now()
		elif student.status != "rejected":
			student.rejected_at = None
	if "registrationDate" in payload and payload["registrationDate"]:
		student.registration_date = payload["registrationDate"]
	if "meta" in payload:
		existing_meta = _meta_dict(student)
		incoming_meta = payload.get("meta") or {}
		if isinstance(incoming_meta, dict):
			merged_meta = {**existing_meta, **incoming_meta}
		else:
			merged_meta = existing_meta
		student.meta = merged_meta

	if "tuitionFee" not in payload and any(key in payload for key in ("batchId", "meta", "courses", "dayChoice", "preferredTime")):
		tuition_courses = _meta_dict(student).get("courses") if isinstance(_meta_dict(student).get("courses"), dict) else {}
		tuition_day_choice = _meta_dict(student).get("dayChoice")
		student.tuition_fee = _calculate_tuition(student.batch, tuition_courses if isinstance(tuition_courses, dict) else {}, tuition_day_choice)

	# If admin changes payment status without sending amountPaid, keep amount_paid aligned with status.
	if "paymentStatus" in payload and "amountPaid" not in payload:
		payment_status = payload.get("paymentStatus")
		tuition = int(getattr(student, "tuition_fee", 0) or 0)
		if payment_status == "paid":
			student.amount_paid = tuition
		elif payment_status == "partial":
			student.amount_paid = round(tuition * 0.5)
		elif payment_status == "not_paid":
			student.amount_paid = 0

	student.save()
	return serialize_student(_student_to_dict(student))


def delete_student(student_id: str) -> bool:
	# Retrieve student to get phone before deletion so we can also cleanup
	student = Student.objects.filter(id=student_id).first()
	if not student:
		return False
	phone = student.phone
	deleted, _ = Student.objects.filter(id=student_id).delete()
	# Also remove any LandingRegistration records that reference the same phone
	# (normalize comparison) so the phone becomes available again.
	try:
		from apps.landing.models import LandingRegistration
		normalized = _normalize_phone(phone)
		if normalized:
			# iterate to avoid database-specific normalization
			for reg in LandingRegistration.objects.only('id', 'phone').iterator():
				if _normalize_phone(reg.phone) == normalized:
					reg.delete()
	except Exception:
		# if landing app/model is not available or deletion fails, ignore to
		# avoid blocking the primary delete operation
		pass

	return bool(deleted)
