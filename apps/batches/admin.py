from django.contrib import admin

from .models import Batch


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "start_date", "end_date", "capacity", "created_at")
	search_fields = ("id", "name")
