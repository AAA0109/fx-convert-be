import copy
import logging

from django.db import migrations

from main.apps.broker.models import BrokerInstrument, Broker


# ============================================

def update_brokers(app, schema_editor):
    instruments_to_add = []

    dry_run = False

    monex = Broker.objects.get(name='Monex USA')
    corpay = Broker.objects.get(name='Corpay')
    nium = Broker.objects.get(name='Nium')

    for bi in BrokerInstrument.objects.filter(broker=corpay):

        monex_bi = copy.copy(bi)
        monex_bi.pk = None
        monex_bi.broker = monex
        instruments_to_add.append(monex_bi)

        if not bi.base_ccy or '-SPOT' in bi.instrument.name:
            nium_bi = copy.copy(bi)
            nium_bi.pk = None
            nium_bi.broker = nium
            instruments_to_add.append(nium_bi)

    if dry_run:
        raise ValueError

    if instruments_to_add and not dry_run:
        BrokerInstrument.objects.bulk_create(instruments_to_add)


# =======================

def update_company_perms(app, schema_editor):
    # ===================

    update = []
    dry_run = False
    broker_names = ['Nium', 'Monex USA']  # change this to add more broker instruments

    # ===================
    ProxyCompany = app.get_model('account', 'Company')
    ProxyUser = app.get_model('account', 'User')
    ProxyCnyExecution = app.get_model('oems', "CnyExecution")
    ProxyBrokerCompanyInstrument = app.get_model('broker', "BrokerCompanyInstrument")
    ProxyBrokerUserInstrument = app.get_model('broker', "BrokerUserInstrument")
    ProxyBrokerInstrument = app.get_model('broker', 'BrokerInstrument')

    for company in ProxyCompany.objects.iterator():
        exec_cfgs = ProxyCnyExecution.objects.filter(company=company)
        users = ProxyUser.objects.filter(company=company)

        logging.debug(f'loading perms for company {company.name} users: {users}')

        for broker_name in broker_names:

            for cny in exec_cfgs:


                proxy_cny = ProxyCnyExecution.objects.get(pk=cny.pk)
                # create spot company perm
                market = f"{cny.fxpair.base_currency.mnemonic}{cny.fxpair.quote_currency.mnemonic}"
                spot_nm = f'{market}-SPOT'
                fwd_nm = f'{market}-BROKEN'

                if broker_name == 'Nium' and cny.spot_rfq_type != 'api':
                    continue

                # get spot instrument
                try:
                    spot_bi = ProxyBrokerInstrument.objects.get(broker__name=broker_name, instrument__name=spot_nm)
                except:
                    # logging.info(f'missing {spot_nm}')
                    spot_bi = None

                try:
                    fwd_bi = ProxyBrokerInstrument.objects.get(broker__name=broker_name, instrument__name=fwd_nm)
                except:
                    # logging.info(f'missing {fwd_nm}')
                    fwd_bi = None

                if not fwd_bi and not spot_bi:
                    continue

                if spot_bi:
                    cp = ProxyBrokerCompanyInstrument(
                        company=company,
                        broker_instrument=spot_bi,
                        staging=proxy_cny.staging,
                        active=proxy_cny.active,
                        use_triggers=proxy_cny.use_triggers,
                        rfq_type=proxy_cny.spot_rfq_type,
                        min_order_size_buy=proxy_cny.min_order_size_to,
                        max_order_size_buy=proxy_cny.max_order_size_to,
                        min_order_size_sell=proxy_cny.min_order_size_from,
                        max_order_size_sell=proxy_cny.max_order_size_from,
                        max_daily_tickets=proxy_cny.max_daily_tickets,
                        unit_order_size_buy=proxy_cny.unit_order_size_to,
                        unit_order_size_sell=proxy_cny.unit_order_size_from,
                    )
                    if not dry_run: cp.save()

                if fwd_bi:
                    cp = ProxyBrokerCompanyInstrument(
                        company=company,
                        broker_instrument=fwd_bi,
                        staging=proxy_cny.staging,
                        active=proxy_cny.active,
                        use_triggers=proxy_cny.use_triggers,
                        rfq_type=proxy_cny.fwd_rfq_type,
                        min_order_size_buy=proxy_cny.min_order_size_to,
                        max_order_size_buy=proxy_cny.max_order_size_to,
                        min_order_size_sell=proxy_cny.min_order_size_from,
                        max_order_size_sell=proxy_cny.max_order_size_from,
                        max_daily_tickets=proxy_cny.max_daily_tickets,
                        unit_order_size_buy=proxy_cny.unit_order_size_to,
                        unit_order_size_sell=proxy_cny.unit_order_size_from,
                    )
                    if not dry_run: cp.save()

                for user in users:

                    # create spot user perm
                    if spot_bi:
                        up = ProxyBrokerUserInstrument(
                            user=user,
                            company=company,
                            broker_instrument=spot_bi,
                            staging=proxy_cny.staging,
                            active=proxy_cny.active,
                            use_triggers=proxy_cny.use_triggers,
                            rfq_type=proxy_cny.fwd_rfq_type,
                            min_order_size_buy=proxy_cny.min_order_size_to,
                            max_order_size_buy=proxy_cny.max_order_size_to,
                            min_order_size_sell=proxy_cny.min_order_size_from,
                            max_order_size_sell=proxy_cny.max_order_size_from,
                            max_daily_tickets=proxy_cny.max_daily_tickets,
                            unit_order_size_buy=proxy_cny.unit_order_size_to,
                            unit_order_size_sell=proxy_cny.unit_order_size_from,
                        )
                        if not dry_run: up.save()

                    # create fwd user perm
                    if fwd_bi:
                        up = ProxyBrokerUserInstrument(
                            user=user,
                            company=company,
                            broker_instrument=fwd_bi,
                            staging=proxy_cny.staging,
                            active=proxy_cny.active,
                            use_triggers=proxy_cny.use_triggers,
                            rfq_type=proxy_cny.fwd_rfq_type,
                            min_order_size_buy=proxy_cny.min_order_size_to,
                            max_order_size_buy=proxy_cny.max_order_size_to,
                            min_order_size_sell=proxy_cny.min_order_size_from,
                            max_order_size_sell=proxy_cny.max_order_size_from,
                            max_daily_tickets=proxy_cny.max_daily_tickets,
                            unit_order_size_buy=proxy_cny.unit_order_size_to,
                            unit_order_size_sell=proxy_cny.unit_order_size_from,
                        )
                        if not dry_run: up.save()

    # ===================

    if dry_run:
        raise ValueError


class Migration(migrations.Migration):
    dependencies = [
        ('broker', '0005_alter_brokercompanyinstrument_default_exec_strat_and_more'),
    ]

    operations = [
        migrations.RunPython(update_brokers),
        migrations.RunPython(update_company_perms),
    ]
