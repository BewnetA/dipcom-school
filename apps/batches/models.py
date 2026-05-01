from django.db import models


class Batch(models.Model):
	id = models.CharField(primary_key=True, max_length=32)
	name = models.CharField(max_length=120)
	start_date = models.DateField()
	end_date = models.DateField()
	capacity = models.PositiveIntegerField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["start_date", "id"]

	def __str__(self) -> str:
		return f"{self.id} - {self.name}"
