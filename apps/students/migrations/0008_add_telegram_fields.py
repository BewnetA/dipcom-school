from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		("students", "0007_student_rejected_at"),
	]

	operations = [
		migrations.AddField(
			model_name="student",
			name="father_name",
			field=models.CharField(blank=True, default="", max_length=120),
		),
		migrations.AddField(
			model_name="student",
			name="telegram_user_id",
			field=models.BigIntegerField(blank=True, null=True, unique=True),
		),
		migrations.AddField(
			model_name="student",
			name="telegram_username",
			field=models.CharField(blank=True, default="", max_length=150),
		),
	]
