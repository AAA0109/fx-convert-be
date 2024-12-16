# Generated by Django 4.2.10 on 2024-03-11 18:51

from django.db import migrations, IntegrityError
from django.conf import settings

import csv
import logging

logger = logging.getLogger(__name__)

def update_cny_execute(app, schema_editor):

	CnyExecution = app.get_model('oems', 'CnyExecution')

	cny = CnyExecution.objects.all()

	for _ in cny:
		if _.fwd_rfq_type != 'unsupported':
			_.spot_rfq_type = 'api'

class Migration(migrations.Migration):
	dependencies = [
		('oems', '0078_rename_rfq_type_cnyexecution_fwd_rfq_type_and_more'),
	]

	operations = [
		migrations.RunPython(update_cny_execute),
	]


