from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("students", "0005_student_graduated_flag"),
    ]

    operations = [
        migrations.AddField(
            model_name="student",
            name="meta",
            field=models.JSONField(default=dict, blank=True),
        ),
    ]
