from __future__ import annotations

from django.http import JsonResponse
from django.urls import path

from .views import BatchDetailView, BatchesCollectionView, NextBatchNameView, TimeslotCollectionView, AvailableTimeslotsView, BatchCompleteView


def batches_health(_request):
	return JsonResponse({"status": "ok", "module": "batches"})


urlpatterns = [
	path("", BatchesCollectionView.as_view(), name="batches-collection"),
	path("next-name/", NextBatchNameView.as_view(), name="batches-next-name"),
	path("timeslots/", TimeslotCollectionView.as_view(), name="batches-timeslots"),
	path("<str:batch_id>/available-timeslots/", AvailableTimeslotsView.as_view(), name="batch-available-timeslots"),
	path("<str:batch_id>/complete/", BatchCompleteView.as_view(), name="batch-complete"),
	path("<str:batch_id>/", BatchDetailView.as_view(), name="batch-detail"),
	path("health/", batches_health, name="batches-health"),
]
