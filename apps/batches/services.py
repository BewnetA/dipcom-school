from __future__ import annotations

from datetime import date
from uuid import uuid4

from django.db.models import Q
from django.utils import timezone

from .models import Batch
from .serializers import serialize_batch, serialize_batches
from .lifecycle import sync_completed_batch_students
from apps.students.models import Student


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
		"capacity": batch.capacity,
	}



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
		}
		for item in items
	]


def _compute_batch_metrics(batch: dict) -> dict:
	students = _batch_students(batch["id"])
	graded = [student for student in students if student.get("grade") is not None]
	employed = len([student for student in students if student.get("employmentStatus") == "yes"])

	today = timezone.localdate()
	end_date = date.fromisoformat(batch["endDate"])
	status = "Active" if end_date >= today else "Completed"
	avg_grade = round(sum(student["grade"] for student in graded) / len(graded)) if graded else 0
	employment_rate = round((employed / len(students)) * 100) if students else 0

	return {
		**batch,
		"status": status,
		"studentCount": len(students),
		"avgGrade": avg_grade,
		"employmentRate": employment_rate,
	}


def list_batches(active_only: bool = False) -> list[dict]:
	sync_completed_batch_students()
	queryset = Batch.objects.all()
	if active_only:
		queryset = queryset.filter(end_date__gte=timezone.localdate())
	items = [_compute_batch_metrics(_batch_to_dict(batch)) for batch in queryset]
	return serialize_batches(items)


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

	batch_id = payload.get("id") or f"b-{uuid4().hex[:8]}"
	while Batch.objects.filter(id=batch_id).exists():
		batch_id = f"b-{uuid4().hex[:8]}"

	batch = Batch.objects.create(
		id=batch_id,
		name=name,
		start_date=payload.get("startDate", timezone.localdate().isoformat()),
		end_date=payload.get("endDate", timezone.localdate().isoformat()),
		capacity=payload.get("capacity"),
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
		batch.start_date = payload["startDate"]
	if "endDate" in payload:
		batch.end_date = payload["endDate"]
	if "capacity" in payload:
		batch.capacity = payload["capacity"]

	batch.save()
	return serialize_batch(_compute_batch_metrics(_batch_to_dict(batch)))


def delete_batch(batch_id: str) -> bool:
	deleted, _ = Batch.objects.filter(id=batch_id).delete()
	return bool(deleted)
