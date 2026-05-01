from __future__ import annotations

from django.utils import timezone

from apps.students.models import Student


def sync_completed_batch_students() -> int:
	"""Mark approved students as graduated when their batch has ended."""
	today = timezone.localdate()
	updated = Student.objects.filter(
		batch__end_date__lt=today,
		status="approved",
		graduated=False,
	).update(graduated=True)
	return int(updated)
