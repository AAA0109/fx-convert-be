# Generated by Django 4.2.10 on 2024-03-11 18:51

from django.db import migrations, IntegrityError
from django.conf import settings

import logging

from main.apps.oems.models   import CnyExecution
from main.apps.broker.models import BrokerCompanyInstrument, BrokerInstrument, BrokerUserInstrument
from main.apps.account.models.company import Company
from main.apps.account.models.user import User

# =======================

def update_company_perms(app, schema_editor):

	# ===================

	update = []
	dry_run = False
	broker_names = ['Corpay'] # change this to add more broker instruments

	# ===================

	for company in Company.objects.iterator():

		exec_cfgs = CnyExecution.objects.filter(company=company)
		users = User.objects.filter(company=company)

		logging.debug(f'loading perms for company {company.name} users: {users}')

		for broker_name in broker_names:

			for cny in exec_cfgs:

				# create spot company perm

				spot_nm = f'{cny.fxpair.market}-SPOT'
				fwd_nm = f'{cny.fxpair.market}-BROKEN'

				# get spot instrument
				try:
					spot_bi = BrokerInstrument.objects.get(broker__name=broker_name, instrument__name=spot_nm)
				except:
					# logging.info(f'missing {spot_nm}')
					spot_bi = None

				try:
					fwd_bi = BrokerInstrument.objects.get(broker__name=broker_name, instrument__name=fwd_nm)
				except:
					# logging.info(f'missing {fwd_nm}')
					fwd_bi = None

				if not fwd_bi and not spot_bi:
					continue

				if spot_bi:
					cp = BrokerCompanyInstrument(
						company=company,
						broker_instrument=spot_bi,
						staging=cny.staging,
						active=cny.active,
						default_exec_strat=cny.default_exec_strat,
						default_hedge_strat=cny.default_hedge_strat,
						default_algo=cny.default_algo,
						use_triggers=cny.use_triggers,
						rfq_type=cny.spot_rfq_type,
						min_order_size_buy=cny.min_order_size_to,
						max_order_size_buy=cny.max_order_size_to,
						min_order_size_sell=cny.min_order_size_from,
						max_order_size_sell=cny.max_order_size_from,
						max_daily_tickets=cny.max_daily_tickets,
						unit_order_size_buy=cny.unit_order_size_to,
						unit_order_size_sell=cny.unit_order_size_from,
					)
					if not dry_run: cp.save()

				if fwd_bi:
					cp = BrokerCompanyInstrument(
						company=company,
						broker_instrument=fwd_bi,
						staging=cny.staging,
						active=cny.active,
						default_exec_strat=cny.default_exec_strat,
						default_hedge_strat=cny.default_hedge_strat,
						default_algo=cny.default_algo,
						use_triggers=cny.use_triggers,
						rfq_type=cny.fwd_rfq_type,
						min_order_size_buy=cny.min_order_size_to,
						max_order_size_buy=cny.max_order_size_to,
						min_order_size_sell=cny.min_order_size_from,
						max_order_size_sell=cny.max_order_size_from,
						max_daily_tickets=cny.max_daily_tickets,
						unit_order_size_buy=cny.unit_order_size_to,
						unit_order_size_sell=cny.unit_order_size_from,
					)
					if not dry_run: cp.save()

				for user in users:

					# create spot user perm
					if spot_bi:
						up = BrokerUserInstrument(
							user=user,
							company=company,
							broker_instrument=spot_bi,
							staging=cny.staging,
							active=cny.active,
							default_exec_strat=cny.default_exec_strat,
							default_hedge_strat=cny.default_hedge_strat,
							default_algo=cny.default_algo,
							use_triggers=cny.use_triggers,
							rfq_type=cny.fwd_rfq_type,
							min_order_size_buy=cny.min_order_size_to,
							max_order_size_buy=cny.max_order_size_to,
							min_order_size_sell=cny.min_order_size_from,
							max_order_size_sell=cny.max_order_size_from,
							max_daily_tickets=cny.max_daily_tickets,
							unit_order_size_buy=cny.unit_order_size_to,
							unit_order_size_sell=cny.unit_order_size_from,
						)
						if not dry_run: up.save()

					# create fwd user perm
					if fwd_bi:
						up = BrokerUserInstrument(
							user=user,
							company=company,
							broker_instrument=fwd_bi,
							staging=cny.staging,
							active=cny.active,
							default_exec_strat=cny.default_exec_strat,
							default_hedge_strat=cny.default_hedge_strat,
							default_algo=cny.default_algo,
							use_triggers=cny.use_triggers,
							rfq_type=cny.fwd_rfq_type,
							min_order_size_buy=cny.min_order_size_to,
							max_order_size_buy=cny.max_order_size_to,
							min_order_size_sell=cny.min_order_size_from,
							max_order_size_sell=cny.max_order_size_from,
							max_daily_tickets=cny.max_daily_tickets,
							unit_order_size_buy=cny.unit_order_size_to,
							unit_order_size_sell=cny.unit_order_size_from,
						)
						if not dry_run: up.save()

				
	# ===================

	if dry_run:
		raise ValueError


# =========

class Migration(migrations.Migration):
	dependencies = [
		('broker', '0001_brokeruserinstrument_brokercompanyinstrument'),
	]

	operations = [
		migrations.RunPython(update_company_perms),
	]