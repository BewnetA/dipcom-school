from django.contrib import admin

from .models import EmploymentCheckin, Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "batch", "payment_status", "grade", "employment_status", "registration_type", "registration_date")
	search_fields = ("id", "name", "phone")
	list_filter = ("payment_status", "employment_status", "batch", "registration_type")


@admin.register(EmploymentCheckin)
class EmploymentCheckinAdmin(admin.ModelAdmin):
	list_display = ("id", "student", "survey", "is_employed", "checked_at")
	list_filter = ("is_employed",)
	search_fields = ("student__name", "student__id")
