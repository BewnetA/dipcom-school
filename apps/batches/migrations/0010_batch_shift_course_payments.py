from django.db import migrations, models


def copy_legacy_course_payments(apps, schema_editor):
	Batch = apps.get_model('batches', 'Batch')
	for batch in Batch.objects.all():
		updates = {}
		if batch.computer_course_payment is not None:
			updates['computer_course_payment_mwf'] = batch.computer_course_payment
			updates['computer_course_payment_tts'] = batch.computer_course_payment
			updates['computer_course_payment_extension'] = batch.computer_course_payment
		if batch.office_course_payment is not None:
			updates['office_course_payment_mwf'] = batch.office_course_payment
			updates['office_course_payment_tts'] = batch.office_course_payment
			updates['office_course_payment_extension'] = batch.office_course_payment
		if updates:
			for key, value in updates.items():
				setattr(batch, key, value)
			batch.save(update_fields=list(updates.keys()) + ['updated_at'])


class Migration(migrations.Migration):

	dependencies = [
		('batches', '0009_convert_is_closed_to_status'),
	]

	operations = [
		migrations.AddField(
			model_name='batch',
			name='computer_course_payment_extension',
			field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
		),
		migrations.AddField(
			model_name='batch',
			name='computer_course_payment_mwf',
			field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
		),
		migrations.AddField(
			model_name='batch',
			name='computer_course_payment_tts',
			field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
		),
		migrations.AddField(
			model_name='batch',
			name='office_course_payment_extension',
			field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
		),
		migrations.AddField(
			model_name='batch',
			name='office_course_payment_mwf',
			field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
		),
		migrations.AddField(
			model_name='batch',
			name='office_course_payment_tts',
			field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
		),
		migrations.RunPython(copy_legacy_course_payments, migrations.RunPython.noop),
	]
