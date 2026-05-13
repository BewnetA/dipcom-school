from django.db import models


class Timeslot(models.Model):
	label = models.CharField(max_length=64, unique=True)
	position = models.PositiveSmallIntegerField(default=1)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ["position", "id"]

	def __str__(self) -> str:
		return self.label


class Batch(models.Model):
	id = models.CharField(primary_key=True, max_length=32)
	name = models.CharField(max_length=120)
	start_date = models.DateField()
	end_date = models.DateField()
	registration_end_date = models.DateField(null=True, blank=True)
	capacity = models.PositiveIntegerField(null=True, blank=True)
	timeslot_1_capacity = models.PositiveIntegerField(null=True, blank=True)
	timeslot_2_capacity = models.PositiveIntegerField(null=True, blank=True)
	timeslot_3_capacity = models.PositiveIntegerField(null=True, blank=True)
	timeslot_4_capacity = models.PositiveIntegerField(null=True, blank=True)
	timeslot_5_capacity = models.PositiveIntegerField(null=True, blank=True)
	extension_capacity = models.PositiveIntegerField(null=True, blank=True)
	computer_course_payment = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
	office_course_payment = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
	status = models.CharField(
		max_length=20,
		choices=[('open', 'Open'), ('closed', 'Closed'), ('completed', 'Completed')],
		default='open'
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["start_date", "id"]

	def __str__(self) -> str:
		return f"{self.id} - {self.name}"
