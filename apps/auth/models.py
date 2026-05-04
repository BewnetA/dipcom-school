from django.conf import settings
from django.db import models


class AuthSession(models.Model):
	token = models.CharField(primary_key=True, max_length=64)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='auth_sessions')
	expires_at = models.DateTimeField()
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'auth_sessions'
		indexes = [models.Index(fields=['expires_at'])]

	def __str__(self) -> str:
		return f'{self.token} - {self.user_id}'
