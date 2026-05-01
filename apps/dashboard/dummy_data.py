from __future__ import annotations

DASHBOARD_DUMMY_DATA = {
	"last_updated": "Today, 09:30 AM",
	"stats": {
		"total_students": 118,
		"active_batches": 3,
		"employment_rate": 67,
		"average_grade": 82,
	},
	"students_per_batch": [
		{"name": "Jan 2026", "batch_id": "batch-jan-2026", "students": 30},
		{"name": "Apr 2026", "batch_id": "batch-apr-2026", "students": 28},
		{"name": "Jul 2026", "batch_id": "batch-jul-2026", "students": 35},
		{"name": "Oct 2026", "batch_id": "batch-oct-2026", "students": 25},
	],
	"employment_breakdown": [
		{"name": "Yes", "value": 53},
		{"name": "No", "value": 26},
	],
	"recent_students": [
		{
			"name": "Maya Ahmed",
			"batch": "Batch Apr 2026",
			"status": "Paid",
			"trend": "↑ New",
		},
		{
			"name": "Hassan Saleh",
			"batch": "Batch Jul 2026",
			"status": "Partial",
			"trend": "↑ Added",
		},
		{
			"name": "Nora Ibrahim",
			"batch": "Batch Jul 2026",
			"status": "Paid",
			"trend": "↑ New",
		},
		{
			"name": "Omar Nasser",
			"batch": "Batch Oct 2026",
			"status": "Not Paid",
			"trend": "↑ Added",
		},
		{
			"name": "Lina Farouk",
			"batch": "Batch Oct 2026",
			"status": "Paid",
			"trend": "↑ New",
		},
	],
	"recent_registrations": [
		{"name": "Maya Ahmed", "batch": "Batch Apr 2026", "type": "Online"},
		{"name": "Hassan Saleh", "batch": "Batch Apr 2026", "type": "In-Person"},
		{"name": "Nora Ibrahim", "batch": "Batch Jul 2026", "type": "Online"},
		{"name": "Omar Nasser", "batch": "Batch Jul 2026", "type": "In-Person"},
		{"name": "Lina Farouk", "batch": "Batch Oct 2026", "type": "Online"},
	],
}
