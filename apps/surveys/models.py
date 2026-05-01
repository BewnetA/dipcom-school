from django.db import models


class Survey(models.Model):
	id = models.CharField(primary_key=True, max_length=32)
	question = models.TextField()
	survey_type = models.CharField(max_length=32, default="yes_no")
	last_sent = models.DateField()
	response_yes = models.PositiveIntegerField(default=0)
	response_no = models.PositiveIntegerField(default=0)

	class Meta:
		ordering = ["-last_sent", "id"]

	def __str__(self) -> str:
		return f"{self.id} - {self.question[:40]}"
