from django.contrib import admin

from .models import LandingRegistration


@admin.register(LandingRegistration)
class LandingRegistrationAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "phone", "batch", "registration_type", "learning_time", "created_at")
	list_filter = ("registration_type", "learning_time")
	search_fields = ("id", "name", "phone")
