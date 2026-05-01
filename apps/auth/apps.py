from django.apps import AppConfig


class DipcomAuthConfig(AppConfig):
	default_auto_field = "django.db.models.BigAutoField"
	name = "apps.auth"
	label = "dipcom_auth"
	verbose_name = "DIPCOM Auth"
