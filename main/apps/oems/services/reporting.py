import logging
import uuid
import csv

import pandas as pd

from datetime import date, datetime

from django.conf import settings

from main.apps.oems.models.ticket import Ticket

from main.apps.currency.models import Currency
from main.apps.oems.backend.date_utils import parse_datetime, parse_date
from main.apps.account.models import Company

from main.apps.notification.services.email.templates import to_html
from post_office.mail import send as send_mail
from pretty_html_table import build_table

from main.apps.marketdata.services.initial_marketdata import get_recent_data
from main.apps.oems.backend.ccy_utils import determine_rate_side

# ======================================

logger = logging.getLogger(__name__)

# ======================================

def save_csv( filename, data ):
	# Open the file in write mode
	with open(filename, 'w', newline='') as csvfile:
		# Create a DictWriter object
		fieldnames = data[0].keys()  # Assuming all dictionaries have the same keys
		writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
		
		# Write the header
		writer.writeheader()
		
		# Write the data
		for row in data:
			writer.writerow(row)

# ======================================

def get_usd_volume( ticket ):
	if ticket.lock_side.mnemonic == 'USD':
		return ticket.amount
	else:
		if ticket.sell_currency.mnemonic == 'USD':
			amounts = ticket.get_payment_amounts()
			return amounts['cntr_amount']
		elif ticket.buy_currency.mnemonic == 'USD':
			amounts = ticket.get_payment_amounts()
			return amounts['amount']
		else:
			usd_ccy = Currency.get_currency(currency='USD')
			if ticket.lock_side.mnemonic == ticket.sell_currency.mnemonic:
				sell_currency = ticket.lock_side
				buy_currency = usd_ccy
			else:
				sell_currency = usd_ccy
				buy_currency = ticket.lock_side
			fxpair, side = determine_rate_side(sell_currency, buy_currency)
			spot_rate, fwd_points, ws_feed = get_recent_data( fxpair, 'spot' )
			rate = spot_rate['mid']

			if fxpair.market[:3] == 'USD':
				usd_volume = round(ticket.amount / rate, 2)
			else:
				usd_volume = round(ticket.amount * rate, 2)

			print( ticket.ticket_id, ticket.market_name, ticket.amount, ticket.lock_side, ticket.side, fxpair.market, side, usd_volume, spot_rate['mid'])

			return usd_volume

def summarize( ticket, rev_share ):
	ret = {}
	for fld in ('ticket_id','broker','transaction_time','amount','value_date','tenor','all_in_rate','market_name','side','broker_id','usd_volume'):
		if fld == 'amount':
			ret[fld] = ticket.amount
			ret['unit'] = ticket.lock_side.mnemonic
			# ret[fld] = f'{ticket.amount} {ticket.lock_side.mnemonic}'
		else:
			ret[fld] = getattr(ticket,fld) if hasattr(ticket,fld) else None
	ret['rev_share'] = rev_share
	ret['approx_usd_revenue'] = ticket.usd_volume * rev_share
	return ret

def float_formatter( x ):
	if isinstance(x, float):
		return f'{x:,.0f}'
	return str(x)

def generate_report( start_date=None, end_date=None, rev_share=0.002, show=False, send=False, recips=None, **kwargs ):

	qry = {}

	if start_date:
		qry['created__gte'] = start_date
		
	if end_date:
		qry['created_lte'] = end_date

	qry['action'] = 'execute'
	qry['phase__in'] = ['SETTLE','RECON']

	queryset = Ticket.objects.filter(**qry)

	summary = {}
	transactions = []

	for ticket in queryset:

		# print('found ticket', ticket)
		dt = ticket.transaction_time or ticket.created
		sort_key = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
		key = dt.strftime('%Y-%m')

		usd_volume = get_usd_volume( ticket )
		if usd_volume is None: continue

		ticket.usd_volume = usd_volume

		if key in summary:
			row = summary[key]
		else:
			row = { 'month': key, 'sort_key': sort_key, 'trades': 0, 'clients': set(), 'brokers': set(), 'num_brokers': 0, 'num_clients': 0, 'trade_volume_usd': 0.0, 'revenue': 0.0 }
			summary[key] = row

		row['trades'] += 1
		row['clients'].add(ticket.company.id)

		if ticket.broker == 'CORPAY_MP':
			ticket.broker == 'CORPAY'

		if ticket.broker: row['brokers'].add( ticket.broker )
		row['trade_volume_usd'] += usd_volume

		if ticket.broker in ('CORPAY','CORPAY_MP'):
			row['revenue'] += (usd_volume*rev_share)
		else: # todo add other brokers
			row['revenue'] += (usd_volume*rev_share)

		transactions.append( summarize(ticket, rev_share) )

	summary = sorted(list(summary.values()), key=lambda x: x['sort_key'])
	if transactions:
		transactions.sort(key=lambda x: (x['transaction_time'] is None, x['transaction_time']))

	index = []
	for row in summary:
		index.append( row['month'] )
		clients = row.pop('clients')
		brokers = row.pop('brokers')
		row['num_clients'] = len(clients)
		row['num_brokers'] = len(brokers)
		del row['sort_key']

	if summary:

		df = pd.DataFrame(summary, index=index)
		float_cols = df.select_dtypes(include=['float']).columns
		df[float_cols] = df[float_cols].applymap(lambda x: f"{x:,.0f}")

		if show:
			logger.info( df )

		if send and recips:

			attachments = {}

			if transactions:
				filename = f'/tmp/transaction-{uuid.uuid4()}.csv'
				save_csv( filename, transactions )
				attachments['transactions.csv'] = filename

			# body = df.to_html(float_format=float_formatter, justify='center',border=1)
			body = build_table(df, 'blue_light')
			subject = f'{settings.APP_ENVIRONMENT}: Revenue Estimate @ {datetime.now().isoformat()}'
			logger.info(f'sending {subject} {recips} {attachments}')
			send_mail(
				recipients=recips,
				sender=settings.DEFAULT_FROM_EMAIL,
				subject=subject,
				priority='now',
				message=body,
				html_message=body,
				attachments=attachments,
			)
			



