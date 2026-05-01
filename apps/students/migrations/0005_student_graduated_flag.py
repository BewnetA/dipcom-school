from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		("students", "0004_backfill_student_status"),
	]

	operations = [
		migrations.AddField(
			model_name="student",
			name="graduated",
			field=models.BooleanField(default=False),
		),
	]
