from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from django.db.models import Q
from django.utils import timezone

from apps.batches.models import Batch
from apps.batches.lifecycle import sync_completed_batch_students
from .models import Student
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


def _student_to_dict(student: Student) -> dict:
	meta = student.meta if hasattr(student, "meta") and isinstance(student.meta, dict) else {}
	sex = meta.get("sex") if meta else None
	if not sex and hasattr(student, "sex"):
		sex = getattr(student, "sex", None)
	return {
		"id": student.id,
		"name": student.name,
		"phone": student.phone,
		"sex": sex,
		"batchId": student.batch_id or "",
		"paymentStatus": student.payment_status,
		"tuitionFee": int(student.tuition_fee),
		# If a record is marked as paid but `amount_paid` is zero (legacy/landing cases),
		# treat it as fully paid so analytics match the students UI where paid implies no due.
		"amountPaid": (int(student.amount_paid) if int(student.amount_paid) > 0 else int(student.tuition_fee)) if student.payment_status == "paid" else int(student.amount_paid),
		"graduated": bool(getattr(student, "graduated", False)),
		"grade": student.grade,
		"employmentStatus": student.employment_status,
		"registrationType": student.registration_type,
		"status": getattr(student, "status", "pending"),
		"rejectedAt": student.rejected_at.isoformat() if getattr(student, "rejected_at", None) else None,
		"registrationDate": student.registration_date.isoformat() if student.registration_date else None,
		"createdAt": student.created_at.isoformat() if getattr(student, "created_at", None) else None,
		"meta": student.meta if hasattr(student, "meta") and student.meta else {},
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
	if graduated == "graduated":
		queryset = queryset.filter(graduated=True)
	elif graduated == "not_graduated":
		queryset = queryset.filter(graduated=False)

	return list(queryset)


def list_students(filters: dict | None = None) -> list[dict]:
	filters = filters or {}
	items = [_student_to_dict(student) for student in _apply_filters(filters)]
	return serialize_students(items)


def cleanup_expired_rejections() -> int:
	cutoff = timezone.now() - timedelta(hours=24)
	expired_ids = list(
		Student.objects.filter(status="rejected", rejected_at__isnull=False, rejected_at__lt=cutoff)
		.only("id")
		.values_list("id", flat=True),
	)
	deleted = 0
	for student_id in expired_ids:
		if delete_student(student_id):
			deleted += 1
	return deleted


def list_approval_students(search: str | None = None) -> list[dict]:
	cleanup_expired_rejections()
	queryset = Student.objects.select_related("batch").filter(registration_type="online").filter(
		Q(status="pending") | Q(status="rejected", rejected_at__gte=timezone.now() - timedelta(hours=24))
	)
	term = (search or "").strip()
	if term:
		queryset = queryset.filter(Q(name__icontains=term) | Q(phone__icontains=term))
	items = sorted(
		[_student_to_dict(student) for student in queryset],
		key=lambda item: (0 if item.get("status") == "pending" else 1, item.get("registrationDate") or ""),
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

	# classification/session/payment
	if _get("classification.session") is None and _get("sessionType") is None:
		missing.append("Session")
	if _get("classification.payment") is None and _get("paymentType") is None:
		missing.append("Payment")

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
	_tuition = int(payload.get("tuitionFee", 12000))

	create_kwargs = {
		"id": student_id,
		"name": payload.get("name", ""),
		"phone": phone,
		"batch": batch,
		"payment_status": _default_payment,
		"tuition_fee": _tuition,
		# default amount paid: explicit payload -> use it; otherwise if online assume fully paid
		"amount_paid": int(
			payload.get(
				"amountPaid",
				(_tuition if payload.get("registrationType", "online") == "online" else 0),
			),
		),
		"graduated": bool(payload.get("graduated", False)),
		"grade": grade,
		"employment_status": payload.get("employmentStatus", "no"),
		"registration_type": payload.get("registrationType", "online"),
		# set status based on registration type: online -> pending, in_person -> approved
		"status": "approved" if payload.get("registrationType", "online") == "in_person" else "pending",
		"meta": payload or {},
	}
	if payload.get("registrationDate"):
		create_kwargs["registration_date"] = payload["registrationDate"]

	student = Student.objects.create(
		**create_kwargs,
	)

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
		student.meta = payload.get("meta") or {}

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
