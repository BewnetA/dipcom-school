from __future__ import annotations

from copy import deepcopy


def serialize_student(student: dict) -> dict:
	return deepcopy(student)


def serialize_students(students: list[dict]) -> list[dict]:
	return [serialize_student(student) for student in students]


def serialize_students_summary(students: list[dict]) -> dict:
	total = len(students)
	paid = len([s for s in students if s.get("paymentStatus") == "paid"])
	employed = len([s for s in students if s.get("employmentStatus") == "yes"])

	return {
		"total": total,
		"paid": paid,
		"notPaid": total - paid,
		"employed": employed,
		"unemployed": total - employed,
	}
