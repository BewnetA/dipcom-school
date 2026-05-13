from django.db import migrations


def seed_timeslots(apps, schema_editor):
    Timeslot = apps.get_model('batches', 'Timeslot')
    defaults = [
        ('3:00 - 4:30', 1),
        ('4:30 - 6:00', 2),
        ('8:00 - 9:30', 3),
        ('9:30 - 11:00', 4),
        ('Night class', 5),
    ]
    for label, position in defaults:
        Timeslot.objects.get_or_create(
            label=label,
            defaults={'position': position, 'is_active': True},
        )


def unseed_timeslots(apps, schema_editor):
    Timeslot = apps.get_model('batches', 'Timeslot')
    labels = ['3:00 - 4:30', '4:30 - 6:00', '8:00 - 9:30', '9:30 - 11:00', 'Night class']
    Timeslot.objects.filter(label__in=labels).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('batches', '0003_timeslot_batch_registration_end_date'),
    ]

    operations = [
        migrations.RunPython(seed_timeslots, unseed_timeslots),
    ]
