from typing import Sequence
from django.db import transaction

from main.apps.account.models.company import Company
from main.apps.broker.models.configuration import (
    ConfigurationTemplate,
    ConfigurationTemplateBroker,
    FeeTemplate
)
from main.apps.broker.models.fee import BrokerFeeCompany, CurrencyFee
from main.apps.marketdata.models.ref.instrument import InstrumentTypes


class BrokerFeeUpdater:
    fee_template:Sequence[FeeTemplate]

    def __init__(self) -> None:
        self.fee_template = FeeTemplate.objects.all()

    def calculate_fee_from_markup(self, markup:float) -> float:
        return markup / 100

    def fill_previous_table_with_spot_fee(self):
        currency_fee = CurrencyFee.objects.filter(instrument_type=None, sell_currency=None)
        for fee in currency_fee:
            try:
                template = FeeTemplate.objects.filter(buy_currency=fee.buy_currency,
                                                      instrument_type=InstrumentTypes.SPOT).first()
                fee.sell_currency = template.sell_currency
                fee.instrument_type = template.instrument_type
                fee.broker_fee = self.calculate_fee_from_markup(markup=template.broker_markup)
                fee.save()
            except Exception as e:
                raise e

    def update_broker_fee_data(self):
        self.fill_previous_table_with_spot_fee()

        for template in self.fee_template:

            config = ConfigurationTemplate.objects.get(
                sell_currency=template.sell_currency,
                buy_currency=template.buy_currency,
                instrument_type=template.instrument_type
            )

            config = ConfigurationTemplateBroker.objects.filter(configuration_template=config)

            brokers = [cnf.broker for cnf in config]

            for broker in brokers:
                try:
                    broker_fee, create = CurrencyFee.objects.get_or_create(
                        sell_currency=template.sell_currency,
                        buy_currency=template.buy_currency,
                        instrument_type=template.instrument_type,
                        broker=broker
                    )
                    broker_fee.broker_fee = self.calculate_fee_from_markup(markup=template.broker_markup)
                    broker_fee.rev_share = 0.0
                    broker_fee.save()
                except Exception as e:
                    raise e


class CompanyBrokerFeeUpdater:
    company:Company

    def __init__(self, company:Company) -> None:
        self.company = company

    def populate_broker_fee(self):
        currency_fees = CurrencyFee.objects.all()

        items = []
        with transaction.atomic():
            for fee in currency_fees:
                company_fee = BrokerFeeCompany(
                    company=self.company,
                    broker=fee.broker,
                    sell_currency=fee.sell_currency,
                    buy_currency=fee.buy_currency,
                    instrument_type=fee.instrument_type,
                    broker_cost=fee.broker_cost,
                    broker_fee=fee.broker_fee,
                    pangea_fee=fee.pangea_fee,
                    rev_share=fee.rev_share,
                    wire_fee=fee.wire_fee,
                )
                items.append(company_fee)

            BrokerFeeCompany.objects.bulk_create(
                objs=items,
                update_conflicts=True,
                unique_fields=[
                    'company',
                    'broker',
                    'sell_currency',
                    'buy_currency',
                    'instrument_type',
                ],
                update_fields=[
                    'broker_cost',
                    'broker_fee',
                    'pangea_fee',
                    'rev_share',
                    'wire_fee'
                ]
            )
