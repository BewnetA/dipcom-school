from __future__ import annotations

from copy import deepcopy


def serialize_dashboard_payload(payload: dict) -> dict:
	"""Return a safe, frontend-ready dashboard payload."""
	stats = payload.get("stats", {})
	return {
		"lastUpdated": payload.get("last_updated"),
		"dashboardStats": {
			"totalStudents": stats.get("total_students", 0),
			"activeBatches": stats.get("active_batches", 0),
			"employmentRate": stats.get("employment_rate", 0),
			"averageGrade": stats.get("average_grade", 0),
		},
		"studentsPerBatch": deepcopy(payload.get("students_per_batch", [])),
		"employmentBreakdown": deepcopy(payload.get("employment_breakdown", [])),
		"recentStudents": deepcopy(payload.get("recent_students", [])),
		"recentRegistrations": deepcopy(payload.get("recent_registrations", [])),
		"registrationBreakdown": deepcopy(payload.get("registration_breakdown", [])),
	}
