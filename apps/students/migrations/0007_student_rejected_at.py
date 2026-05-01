from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		("students", "0006_student_meta"),
	]

	operations = [
		migrations.AddField(
			model_name="student",
			name="rejected_at",
			field=models.DateTimeField(blank=True, null=True),
		),
	]