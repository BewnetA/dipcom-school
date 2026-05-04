import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from django.contrib.auth.models import User
from apps.auth.services import login, get_user_by_token

username = 'tempadmin'
password = 'TempPass123!'
if not User.objects.filter(username=username).exists():
    u = User.objects.create_user(username=username, password=password, email='temp@example.com', first_name='Temp', last_name='Admin')
    u.is_staff = True
    u.is_superuser = True
    u.save()
    print('created user', username)
else:
    print('user exists')

res = login(username, password)
print('login result:', res)
if res and isinstance(res, dict):
    print('me:', get_user_by_token(res['token']))
else:
    print('login failed')
