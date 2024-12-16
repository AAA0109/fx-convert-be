import logging
from typing import Dict, Any

from django.db import transaction

from main.apps.account.models import Company, User
from main.apps.broker.models import ConfigurationTemplate, BrokerInstrument, \
    BrokerCompanyInstrument
from main.apps.currency.models import FxPair
from main.apps.oems.models import CnyExecution

logger = logging.getLogger(__name__)


class BrokerConfigurationService:
    @staticmethod
    def populate_for_company(company: Company):
        results = {
            'success': False,
            'message': '',
            'cny_executions_created': 0,
            'cny_executions_updated': 0,
            'broker_company_instruments_created': 0,
            'broker_company_instruments_updated': 0
        }

        try:
            with transaction.atomic():
                grouped_configs: Dict[str, Dict[str, Any]] = {}
                templates = ConfigurationTemplate.objects.all().select_related('sell_currency', 'buy_currency',
                                                                               'preferred_broker')
                for template in templates:
                    fx_pair = FxPair.get_pair(f"{template.sell_currency}/{template.buy_currency}")
                    if not fx_pair:
                        logger.error(f"FxPair not found, "
                                     f"Unable to populate configuration for: "
                                     f"{template.sell_currency}{template.buy_currency}")
                        continue
                    fx_pair_key = f"{fx_pair.base_currency.mnemonic}{fx_pair.quote_currency.mnemonic}"
                    if fx_pair_key not in grouped_configs:
                        grouped_configs[fx_pair_key] = {
                            "fx_pair": fx_pair,
                            "instrument_config": {},
                            "broker_capabilities": [],
                        }
                    config = grouped_configs[fx_pair_key]

                    # Dynamically add or update instrument type data
                    instrument_type_key = template.instrument_type
                    if instrument_type_key not in config["instrument_config"]:
                        config["instrument_config"][instrument_type_key] = {}
                    config["instrument_config"][instrument_type_key][
                        "preferred_broker"] = template.preferred_broker.broker_provider
                    config["instrument_config"][instrument_type_key]["broker_markup"] = 0.0

                    # Dynamically add or update broker capabilities
                    for ctb in template.configurationtemplatebroker_set.all():
                        broker_capability = next(
                            (bc for bc in config["broker_capabilities"] if bc["broker"] == ctb.broker.name), None)
                        if broker_capability is None:
                            config["broker_capabilities"].append({
                                "broker": ctb.broker.broker_provider,
                                "api": ctb.api
                            })
                        else:
                            # Set to True if any template has API True for this broker
                            broker_capability["api"] |= ctb.api

                for fx_pair_key, config in grouped_configs.items():
                    fx_pair = config['fx_pair']
                    instrument_config = config['instrument_config']

                    # Step 2: Insert into CnyExecution
                    cny_execution_data = {
                        'company': company,
                        'fxpair': fx_pair,
                        'use_triggers': True,
                        'active': True,
                        'spot_rfq_dest': 'RFQ',
                        'fwd_rfq_dest': 'RFQ',
                        'spot_dest': 'CORPAY',
                        'fwd_dest': 'CORPAY',
                        'max_tenor': CnyExecution.Tenors._1Y.value,
                        'fwd_rfq_type': CnyExecution.RfqTypes.UNSUPPORTED
                    }

                    # Set spot and forward data if available
                    if ConfigurationTemplate.InstrumentTypes.SPOT in instrument_config:
                        ic = instrument_config[ConfigurationTemplate.InstrumentTypes.SPOT]
                        cny_execution_data['spot_broker'] = ic['preferred_broker']
                        preferred_broker_api = bool(bc["api"] for bc in config["broker_capabilities"] if
                                                    bc["broker"] == ic['preferred_broker'])
                        cny_execution_data[
                            'spot_rfq_type'] = CnyExecution.RfqTypes.API if preferred_broker_api else CnyExecution.RfqTypes.MANUAL

                    if ConfigurationTemplate.InstrumentTypes.FORWARD in instrument_config:
                        ic = instrument_config[ConfigurationTemplate.InstrumentTypes.FORWARD]
                        cny_execution_data['fwd_broker'] = ic['preferred_broker']
                        preferred_broker_api = bool(bc["api"] for bc in config["broker_capabilities"] if
                                                    bc["broker"] == ic[
                                                        'preferred_broker'])
                        cny_execution_data[
                            'fwd_rfq_type'] = CnyExecution.RfqTypes.API if preferred_broker_api else CnyExecution.RfqTypes.MANUAL

                    if ConfigurationTemplate.InstrumentTypes.NDF in instrument_config:
                        ic = instrument_config[ConfigurationTemplate.InstrumentTypes.NDF]
                        cny_execution_data['fwd_broker'] = ic['preferred_broker']
                        cny_execution_data['fwd_rfq_type'] = CnyExecution.RfqTypes.MANUAL

                    # default to spot broker if no fwd broker is configured in template
                    if 'fwd_broker' not in cny_execution_data:
                        cny_execution_data['fwd_broker'] = cny_execution_data['spot_broker']
                        cny_execution_data['fwd_rfq_type'] = CnyExecution.RfqTypes.UNSUPPORTED

                    cny_execution, created = CnyExecution.objects.update_or_create(
                        company=company,
                        fxpair=fx_pair,
                        defaults=cny_execution_data
                    )
                    if created:
                        results['cny_executions_created'] += 1
                    else:
                        results['cny_executions_updated'] += 1

                    # Step 3: Populate BrokerCompanyInstrument
                    spot_nm = f"{fx_pair_key}-SPOT"
                    fwd_nm = f"{fx_pair_key}-FWD"
                    try:
                        spot_bi = BrokerInstrument.objects.get(
                            broker__broker_provider=cny_execution_data['spot_broker'],
                            instrument__name=spot_nm
                        )
                    except:
                        spot_bi = None

                    try:
                        fwd_bi = BrokerInstrument.objects.get(
                            broker__broker_provider=cny_execution_data['fwd_broker'],
                            instrument__name=fwd_nm
                        )
                    except:
                        fwd_bi = None

                    bi_defaults = {
                        "active": False,
                        "use_triggers": cny_execution.use_triggers,
                        "max_order_size_buy": 15500000000,
                        "max_order_size_sell": 15500000000,
                        "max_tenor_months": 13
                    }

                    if spot_bi:
                        spot_bi_defaults = bi_defaults
                        spot_bi_defaults['rfq_type'] = cny_execution.spot_rfq_type
                        spot_bci, spot_bci_created = BrokerCompanyInstrument.objects.get_or_create(
                            company=company,
                            broker_instrument=spot_bi,
                            defaults=spot_bi_defaults
                        )
                        if spot_bci_created:
                            results['broker_company_instruments_created'] += 1
                        else:
                            results['broker_company_instruments_updated'] += 1
                    else:
                        spot_bci = None

                    if fwd_bi:
                        fwd_bi_defaults = bi_defaults
                        fwd_bi_defaults['rfq_type'] = cny_execution.fwd_rfq_type
                        fwd_bci, fwd_bci_created = BrokerCompanyInstrument.objects.get_or_create(
                            company=company,
                            broker_instrument=fwd_bi,
                            defaults=fwd_bi_defaults
                        )
                        if fwd_bci_created:
                            results['broker_company_instruments_created'] += 1
                        else:
                            results['broker_company_instruments_updated'] += 1
                    else:
                        fwd_bci = None
            results['success'] = True
            results['message'] = f"Successfully populated data for company: {company.name}"

        except Exception as e:
            logger.exception(e)
            results['message'] = f"Error populating execution configuration  data for {company.pk} - {company.name}"

        return results
