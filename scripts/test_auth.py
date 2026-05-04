import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from apps.auth.services import login, get_user_by_token
from django.contrib.auth.models import User
user = User.objects.filter(is_staff=True).first()
print('found user', user and user.username)
if user:
    res = login(user.username, 'wrongpass')
    print('login wrongpass', res)
    print('get_user_by_token bogus', get_user_by_token('bogus_token'))
    # create a test session for user
    from apps.auth.models import AuthSession
    from datetime import datetime, timezone, timedelta
    token = 'testtoken123'
    AuthSession.objects.update_or_create(token=token, defaults={'user': user, 'expires_at': datetime.now(timezone.utc) + timedelta(hours=1)})
    print('created test session')
    print('get_user_by_token testtoken123 ->', get_user_by_token(token))
else:
    print('no staff users found')
