from __future__ import annotations

from datetime import datetime

from apps.batches.services import list_batches
from apps.students.services import list_students
from apps.students.services import _followup_summary

from .serializers import serialize_analytics_payload


def _registration_trend(students: list[dict]) -> list[dict]:
	month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
	today = datetime.now()
	month_slots = []
	for offset in range(5, -1, -1):
		total_month = (today.year * 12 + (today.month - 1)) - offset
		year = total_month // 12
		month = (total_month % 12) + 1
		month_slots.append((year, month))

	counts = {f"{year}-{str(month).zfill(2)}": 0 for year, month in month_slots}
	for student in students:
		created_at = student.get("createdAt")
		if not created_at:
			continue
		try:
			created_date = datetime.fromisoformat(created_at)
		except ValueError:
			continue
		month_key = f"{created_date.year}-{str(created_date.month).zfill(2)}"
		if month_key in counts:
			counts[month_key] += 1

	points = []
	for year, month in month_slots:
		month_key = f"{year}-{str(month).zfill(2)}"

		points.append(
			{
				"month": month_key,
				"label": f"{month_names[month - 1]} {year}",
				"count": counts.get(month_key, 0),
			}
		)

	return points


def get_analytics_overview() -> dict:
	# Analytics should reflect only students that have reached the Students page.
	# Pending/rejected approvals remain out of counts until they become approved.
	students = list_students({"status": "approved"})
	batches = list_batches()

	# registration breakdown: online vs in-person vs bot, based only on approved students
	registration_counts = {"online": 0, "in_person": 0, "bot": 0}
	for student in students:
		type_key = (student.get("registrationType") or "online").replace("-", "_")
		if type_key == "in_person":
			registration_counts["in_person"] += 1
		elif type_key == "bot":
			registration_counts["bot"] += 1
		else:
			registration_counts["online"] += 1


	batch_by_id = {batch["id"]: batch for batch in batches}
	today = datetime.now()

	employed_count = len([student for student in students if student.get("employmentStatus") == "yes"])
	unemployed_count = len([student for student in students if student.get("employmentStatus") == "no"])

	graded_students = [student for student in students if student.get("grade") is not None]
	total_students = len(students)
	active_batches = len(list_batches(active_only=True))

	employment_rate = round((employed_count / (employed_count + unemployed_count)) * 100) if (employed_count + unemployed_count) else 0
	average_grade = round(sum(student["grade"] for student in graded_students) / len(graded_students)) if graded_students else 0

	recent_students = []
	for index, student in enumerate(list(reversed(students[-5:]))):
		batch_name = batch_by_id.get(student["batchId"], {}).get("name", "N/A")
		if student["paymentStatus"] == "paid":
			status = "Paid"
		elif student["paymentStatus"] == "partial":
			status = "Partial"
		else:
			status = "Not Paid"

		recent_students.append(
			{
				"name": student["name"],
				"batch": batch_name,
				"status": status,
				"trend": "↑ New" if index % 2 == 0 else "↑ Added",
			}
		)

	recent_registrations = []
	recent_sorted_students = sorted(
		students,
		key=lambda item: item.get("createdAt") or item.get("registrationDate") or "",
		reverse=True,
	)
	for student in recent_sorted_students[:5]:
		batch_name = batch_by_id.get(student.get("batchId", ""), {}).get("name", "N/A")
		registration_type = str(student.get("registrationType", "online")).replace("_", " ").title()
		recent_registrations.append(
			{
				"name": student.get("name", ""),
				"batch": batch_name,
				"type": registration_type,
			}
		)

	students_per_batch = [
		{
			"name": batch["name"].replace("Batch ", ""),
			"batchId": batch["id"],
			"students": len([student for student in students if student["batchId"] == batch["id"]]),
		}
		for batch in batches
	]

	payment_by_batch = []
	for batch in batches:
		batch_students = [student for student in students if student["batchId"] == batch["id"]]
		collected = sum(int(student.get("amountPaid", 0)) for student in batch_students)
		due = sum(max(int(student.get("tuitionFee", 0)) - int(student.get("amountPaid", 0)), 0) for student in batch_students)
		payment_by_batch.append(
			{
				"batchId": batch["id"],
				"name": batch["name"],
				"collected": collected,
				"due": due,
			}
		)

	total_collected = sum(item["collected"] for item in payment_by_batch)
	total_due = sum(item["due"] for item in payment_by_batch)

	employment_breakdown = [
		{"name": "Yes", "value": employed_count},
		{"name": "No", "value": unemployed_count},
	]

	# gender breakdown (male / female)
	male_count = len([s for s in students if str(s.get("sex", "")).lower() in ("male", "m")])
	female_count = len([s for s in students if str(s.get("sex", "")).lower() in ("female", "f", "woman", "women")])
	gender_breakdown = [
		{"name": "Male", "value": male_count},
		{"name": "Female", "value": female_count},
	]

	# course breakdown: computer vs office (from student.meta.courses)
	computer_count = 0
	office_count = 0
	for s in students:
		meta = s.get("meta") or {}
		courses = meta.get("courses") if isinstance(meta, dict) else None
		if isinstance(courses, dict):
			if courses.get("computer"):
				computer_count += 1
			if courses.get("office"):
				office_count += 1
	course_breakdown = [
		{"name": "Computer Maintenance", "value": computer_count},
		{"name": "Office Machine Maintenance", "value": office_count},
	]

	def in_range(value, low, high):
		return value is not None and low <= value < high

	grade_distribution = [
		{"name": "50-59", "count": len([s for s in students if in_range(s.get("grade"), 50, 60)])},
		{"name": "60-69", "count": len([s for s in students if in_range(s.get("grade"), 60, 70)])},
		{"name": "70-79", "count": len([s for s in students if in_range(s.get("grade"), 70, 80)])},
		{"name": "80-89", "count": len([s for s in students if in_range(s.get("grade"), 80, 90)])},
		{"name": "90-100", "count": len([s for s in students if s.get("grade") is not None and s.get("grade") >= 90])},
	]

	registrations_over_time = _registration_trend(students)

	batch_performance = []
	for batch in batches:
		batch_students = [student for student in students if student["batchId"] == batch["id"]]
		graded = [student for student in batch_students if student.get("grade") is not None]
		average = (sum(student["grade"] for student in graded) / len(graded)) if graded else 0
		batch_performance.append({"name": batch["name"], "avgGrade": average})

	best_performing_batch = max(batch_performance, key=lambda item: item["avgGrade"]) if batch_performance else {"name": "N/A", "avgGrade": 0}
	follow_up_survey = _followup_summary()

	payload = {
		"totalStudents": total_students,
		"activeBatches": active_batches,
		"employmentRate": employment_rate,
		"averageGrade": average_grade,
		"registrationBreakdown": [
			{"name": "Online", "value": registration_counts.get("online", 0)},
			{"name": "In Person", "value": registration_counts.get("in_person", 0)},
			{"name": "Bot", "value": registration_counts.get("bot", 0)},
		],
		"genderBreakdown": gender_breakdown,
		"courseBreakdown": course_breakdown,
		"dashboardStats": {
			"totalStudents": total_students,
			"activeBatches": active_batches,
			"employmentRate": employment_rate,
			"averageGrade": average_grade,
		},
		"recentStudents": recent_students,
		"recentRegistrations": recent_registrations,
		"lastUpdated": datetime.now().strftime("%b %d, %Y %I:%M %p"),
		"studentsPerBatch": students_per_batch,
		"paymentByBatch": payment_by_batch,
		"totalCollected": total_collected,
		"totalDue": total_due,
		"employmentBreakdown": employment_breakdown,
		"gradeDistribution": grade_distribution,
		"registrationsOverTime": registrations_over_time,
		"bestPerformingBatch": best_performing_batch,
		"followUpSurvey": follow_up_survey,
	}

	return serialize_analytics_payload(payload)
