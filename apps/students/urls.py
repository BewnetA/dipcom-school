from __future__ import annotations

from django.http import JsonResponse
from django.urls import path

from .views import (
	StudentDetailView,
	StudentsCollectionView,
	StudentsSummaryView,
	PendingStudentsView,
	approve_student,
	reject_student,
)


def students_health(_request):
	return JsonResponse({"status": "ok", "module": "students"})


urlpatterns = [
	path("", StudentsCollectionView.as_view(), name="students-collection"),
	path("summary/", StudentsSummaryView.as_view(), name="students-summary"),
	path("pending/", PendingStudentsView.as_view(), name="students-pending"),
	path("<str:student_id>/approve/", approve_student, name="student-approve"),
	path("<str:student_id>/reject/", reject_student, name="student-reject"),
	path("<str:student_id>/", StudentDetailView.as_view(), name="student-detail"),
	path("health/", students_health, name="students-health"),
]
