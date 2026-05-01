from django.contrib import admin

from .models import Survey


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
	list_display = ("id", "question", "survey_type", "last_sent", "response_yes", "response_no")
	search_fields = ("id", "question")
	list_filter = ("survey_type",)
