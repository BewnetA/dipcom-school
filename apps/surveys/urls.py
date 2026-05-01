from __future__ import annotations

from django.http import JsonResponse
from django.urls import path

from .views import (
	SurveyDetailView,
	SurveySendAgainView,
	SurveyStatsView,
	SurveysCollectionView,
)


def surveys_health(_request):
	return JsonResponse({"status": "ok", "module": "surveys"})


urlpatterns = [
	path("", SurveysCollectionView.as_view(), name="surveys-collection"),
	path("<str:survey_id>/", SurveyDetailView.as_view(), name="survey-detail"),
	path("<str:survey_id>/stats/", SurveyStatsView.as_view(), name="survey-stats"),
	path("<str:survey_id>/send/", SurveySendAgainView.as_view(), name="survey-send"),
	path("health/", surveys_health, name="surveys-health"),
]
