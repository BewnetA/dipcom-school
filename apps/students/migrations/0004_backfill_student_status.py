from __future__ import annotations

from django.db import migrations


def forwards(apps, schema_editor):
    Student = apps.get_model("students", "Student")
    for student in Student.objects.all():
        student.status = "approved" if student.registration_type == "in_person" else "pending"
        student.save(update_fields=["status"])


def backwards(apps, schema_editor):
    Student = apps.get_model("students", "Student")
    Student.objects.all().update(status="pending")


class Migration(migrations.Migration):

    dependencies = [
        ("students", "0003_add_status_field"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
