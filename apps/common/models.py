from django.db import models


class BotUser(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    full_name = models.CharField(max_length=255)
    father_name = models.CharField(max_length=120, blank=True, default="")
    phone_number = models.CharField(max_length=32, blank=True, default="")
    username = models.CharField(max_length=150, blank=True, default="")
    status = models.CharField(max_length=32, default="pending")
    registered_at = models.DateTimeField(auto_now_add=True)
    enrolled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "users"

    def __str__(self) -> str:
        return f"{self.user_id} - {self.full_name}"


class BotModule(models.Model):
    module_name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "modules"

    def __str__(self) -> str:
        return self.module_name


class BotResource(models.Model):
    module = models.ForeignKey("common.BotModule", on_delete=models.CASCADE, related_name="resources")
    file_id = models.TextField()
    file_name = models.CharField(max_length=255, blank=True, default="")
    file_type = models.CharField(max_length=50, blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "resources"

    def __str__(self) -> str:
        return f"{self.module.module_name} - {self.file_name or self.file_id}"


class BotLog(models.Model):
    user_id = models.BigIntegerField(null=True, blank=True)
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "logs"

    def __str__(self) -> str:
        return f"{self.timestamp} - {self.action}"


class SystemSetting(models.Model):
    key = models.CharField(max_length=120, unique=True)
    value_json = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_settings"

    def __str__(self) -> str:
        return self.key
