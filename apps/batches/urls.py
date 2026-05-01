from __future__ import annotations

from django.http import JsonResponse
from django.urls import path

from .views import BatchDetailView, BatchesCollectionView


def batches_health(_request):
	return JsonResponse({"status": "ok", "module": "batches"})


urlpatterns = [
	path("", BatchesCollectionView.as_view(), name="batches-collection"),
	path("<str:batch_id>/", BatchDetailView.as_view(), name="batch-detail"),
	path("health/", batches_health, name="batches-health"),
]
