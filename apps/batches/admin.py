from django.contrib import admin

from .models import Batch, Timeslot


@admin.register(Timeslot)
class TimeslotAdmin(admin.ModelAdmin):
	list_display = ("label", "position", "is_active")
	list_filter = ("is_active",)
	search_fields = ("label",)


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "start_date", "end_date", "registration_end_date", "capacity", "created_at")
	search_fields = ("id", "name")
