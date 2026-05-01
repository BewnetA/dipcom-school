from django.db import models
from django.utils import timezone


class Student(models.Model):
	REGISTRATION_TYPE_CHOICES = (("online", "Online"), ("in_person", "In-Person"))

	id = models.CharField(primary_key=True, max_length=32)
	name = models.CharField(max_length=120)
	phone = models.CharField(max_length=32, blank=True, default="")
	batch = models.ForeignKey(
		"batches.Batch",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="students",
		db_column="batch_id",
	)
	payment_status = models.CharField(max_length=20, default="not_paid")
	tuition_fee = models.PositiveIntegerField(default=12000)
	amount_paid = models.PositiveIntegerField(default=0)
	graduated = models.BooleanField(default=False)
	meta = models.JSONField(default=dict, blank=True)
	grade = models.PositiveSmallIntegerField(null=True, blank=True)
	employment_status = models.CharField(max_length=20, default="no")
	registration_type = models.CharField(max_length=20, choices=REGISTRATION_TYPE_CHOICES, default="online")

	STATUS_CHOICES = (("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"))
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
	rejected_at = models.DateTimeField(null=True, blank=True)
	registration_date = models.DateField(default=timezone.now)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["id"]
		indexes = [
			models.Index(fields=["batch"]),
			models.Index(fields=["payment_status"]),
			models.Index(fields=["employment_status"]),
		]

	def __str__(self) -> str:
		return f"{self.id} - {self.name}"


class EmploymentCheckin(models.Model):
	student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="employment_checkins")
	survey = models.ForeignKey("surveys.Survey", on_delete=models.SET_NULL, null=True, blank=True, related_name="employment_checkins")
	is_employed = models.BooleanField()
	checked_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-checked_at", "-id"]
