from __future__ import annotations

from django.urls import path

from .views import CourseFeesSettingsView


urlpatterns = [
    path("course-fees/", CourseFeesSettingsView.as_view(), name="settings-course-fees"),
]
