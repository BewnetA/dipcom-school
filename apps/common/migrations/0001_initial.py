from django.db import migrations, models


class Migration(migrations.Migration):

	initial = True

	dependencies = []

	operations = [
		migrations.CreateModel(
			name="BotUser",
			fields=[
				("user_id", models.BigIntegerField(primary_key=True, serialize=False)),
				("full_name", models.CharField(max_length=255)),
				("father_name", models.CharField(blank=True, default="", max_length=120)),
				("phone_number", models.CharField(blank=True, default="", max_length=32)),
				("username", models.CharField(blank=True, default="", max_length=150)),
				("status", models.CharField(default="pending", max_length=32)),
				("registered_at", models.DateTimeField(auto_now_add=True)),
				("enrolled_at", models.DateTimeField(blank=True, null=True)),
			],
			options={"db_table": "users"},
		),
		migrations.CreateModel(
			name="BotModule",
			fields=[
				("id", models.BigAutoField(primary_key=True, serialize=False)),
				("module_name", models.CharField(max_length=255, unique=True)),
				("created_at", models.DateTimeField(auto_now_add=True)),
				("created_by", models.BigIntegerField(blank=True, null=True)),
			],
			options={"db_table": "modules"},
		),
		migrations.CreateModel(
			name="BotResource",
			fields=[
				("id", models.BigAutoField(primary_key=True, serialize=False)),
				("file_id", models.TextField()),
				("file_name", models.CharField(blank=True, default="", max_length=255)),
				("file_type", models.CharField(blank=True, default="", max_length=50)),
				("uploaded_at", models.DateTimeField(auto_now_add=True)),
				("uploaded_by", models.BigIntegerField(blank=True, null=True)),
				(
					"module",
					models.ForeignKey(
						on_delete=models.deletion.CASCADE,
						related_name="resources",
						to="common.botmodule",
					),
				),
			],
			options={"db_table": "resources"},
		),
		migrations.CreateModel(
			name="BotLog",
			fields=[
				("id", models.BigAutoField(primary_key=True, serialize=False)),
				("user_id", models.BigIntegerField(blank=True, null=True)),
				("action", models.CharField(max_length=255)),
				("details", models.TextField(blank=True, default="")),
				("timestamp", models.DateTimeField(auto_now_add=True)),
			],
			options={"db_table": "logs"},
		),
	]
