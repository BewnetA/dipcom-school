from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("students", "0002_employmentcheckin_student_created_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="student",
            name="status",
            field=models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")], default="pending", max_length=20),
        ),
    ]
