from __future__ import annotations

from copy import deepcopy


def serialize_dashboard_payload(payload: dict) -> dict:
	"""Return a safe, frontend-ready dashboard payload."""
	return {
		"lastUpdated": payload.get("last_updated"),
		"dashboardStats": deepcopy(payload.get("stats", {})),
		"studentsPerBatch": deepcopy(payload.get("students_per_batch", [])),
		"employmentBreakdown": deepcopy(payload.get("employment_breakdown", [])),
		"recentStudents": deepcopy(payload.get("recent_students", [])),
		"recentRegistrations": deepcopy(payload.get("recent_registrations", [])),
	}
