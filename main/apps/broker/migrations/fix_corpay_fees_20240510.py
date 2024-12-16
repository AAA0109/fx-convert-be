# Generated by Django 4.2.10 on 2024-03-11 18:51

from django.db import migrations, IntegrityError
from django.conf import settings

from main.apps.oems.backend.utils import load_yml, Expand
from main.apps.broker.models.constants import FeeType, BrokerExecutionMethodOptions, ExecutionTypes, ApiTypes, FundingModel
from main.apps.oems.backend.ccy_utils import check_direction

import csv
import logging

logger = logging.getLogger(__name__)

def parse_row( row ):
	for k, v in row.items():
		if v == '':
			row[k] = None
		elif '%' in v:
			row[k] = float(v.replace('%',''))
		else:
			row[k] = v.upper()
			
	return row

def update_corpay_fees(app, schema_editor):

	index = {}

	path = Expand(__file__) + '/PANGEA_CORPAY1.csv'
	with open( path ) as f:
		reader = csv.DictReader(f, delimiter=',')
		for row in reader:
			prow = parse_row( row )
			index[ row['CURRENCY'] ] = prow

	CurrencyFee = app.get_model('broker', 'CurrencyFee')

	fees = CurrencyFee.objects.all()

	for fee in fees:
		if fee.broker.name == 'Corpay':
			try:
				row = index[ fee.currency.mnemonic ]
			except KeyError:
				print('skipping', fee.currency.mnemonic)
				continue

			if row['PANGEA_FEE'] is None: continue

			pfee = round(row['PANGEA_FEE'] / 100.0, 4)

			if pfee != fee.cost:
				print( 'updating', fee.broker.name, fee.currency.mnemonic, fee.cost, pfee )
				fee.cost = pfee
				fee.save()

	
class Migration(migrations.Migration):
	dependencies = [
		('broker', 'sec_master_populate1'),
	]

	operations = [
		migrations.RunPython(update_corpay_fees),
	]
