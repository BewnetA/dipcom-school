from __future__ import annotations

from apps.analytics.services import get_analytics_overview

from .serializers import serialize_dashboard_payload


def get_dashboard_overview() -> dict:
	analytics = get_analytics_overview()
	payload = {
		"last_updated": analytics.get("lastUpdated"),
		"stats": {
			"total_students": analytics.get("totalStudents", 0),
			"active_batches": analytics.get("activeBatches", 0),
			"employment_rate": analytics.get("employmentRate", 0),
			"average_grade": analytics.get("averageGrade", 0),
		},
		"students_per_batch": analytics.get("studentsPerBatch", []),
		"employment_breakdown": analytics.get("employmentBreakdown", []),
		"recent_students": analytics.get("recentStudents", []),
		"recent_registrations": analytics.get("recentRegistrations", []),
	}
	return serialize_dashboard_payload(payload)
