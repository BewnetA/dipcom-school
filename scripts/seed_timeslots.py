import django
import os
from datetime import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()

from apps.batches.models import Timeslot

PREDEFINED = [
    ("3:00 - 4:30", time(15, 0), time(16, 30), False),
    ("4:30 - 6:00", time(16, 30), time(18, 0), False),
    ("8:00 - 9:30", time(8, 0), time(9, 30), False),
    ("9:30 - 11:00", time(9, 30), time(11, 0), False),
    ("Night", None, None, True),
]

for label, start, end, is_night in PREDEFINED:
    obj, created = Timeslot.objects.get_or_create(label=label, defaults={'start_time': start, 'end_time': end, 'is_night': is_night})
    print('created' if created else 'exists', obj)
