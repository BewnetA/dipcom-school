from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("landing", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="landingregistration",
            name="meta",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
