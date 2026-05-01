from django.db import models


class LandingRegistration(models.Model):
	id = models.CharField(primary_key=True, max_length=32)
	name = models.CharField(max_length=120)
	phone = models.CharField(max_length=32)
	batch = models.ForeignKey("batches.Batch", on_delete=models.SET_NULL, null=True, blank=True, related_name="landing_registrations")
	registration_type = models.CharField(max_length=20, default="online")
	learning_time = models.CharField(max_length=20, default="morning")
	# store arbitrary extra form fields from the landing registration
	meta = models.JSONField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at", "id"]

	def __str__(self) -> str:
		return f"{self.id} - {self.name}"
