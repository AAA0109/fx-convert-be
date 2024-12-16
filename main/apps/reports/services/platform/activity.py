import pandas as pd

from main.apps.account.models import CashFlow
from main.apps.cashflow.models import SingleCashFlow
from main.apps.corpay.models import SpotRate
from main.apps.oems.models import Ticket
from main.apps.reports.services.platform import PlatformReportingService


class PlatformActivityReportingService(PlatformReportingService):
    def __init__(
        self,
        report_name: str,
        report_output_type: PlatformReportingService.ReportType,
        frequency: PlatformReportingService.Frequency
    ):
        self.report_name = report_name
        self.frequency = frequency
        self.report_output_type = report_output_type
        super().__init__(
            report_name=report_name,
            report_output_type=report_output_type,
            frequency=frequency,
        )

    def get_data(self):
        qs_cashflow_old = CashFlow.objects.filter(
            created__gte=self.start_date,
            created__lte=self.end_date
        ).values_list(
            'id',
            'account__company__name',
            'currency__mnemonic',
            'amount',
            'status',
            'date',
            'end_date',
            'periodicity',
            'created',
            'modified',
            named=True
        ).iterator()
        df_cashflow_old = pd.DataFrame(list(qs_cashflow_old))

        qs_cashflow_new = (SingleCashFlow.objects.filter(
            created__gte=self.start_date,
            created__lte=self.end_date,
        ).exclude(
            status=SingleCashFlow.Status.DRAFT
        ).values_list(
            'id',
            'company__name',
            'buy_currency__mnemonic',
            'sell_currency__mnemonic',
            'lock_side__mnemonic',
            'amount',
            'status',
            'pay_date',
            'created',
            'modified',
            named=True
        ).iterator())
        df_cashflow_new = pd.DataFrame(list(qs_cashflow_new))

        qs_oems_ticket = Ticket.objects.filter(
            created__gte=self.start_date,
            created__lte=self.end_date,
            draft=False
        ).values_list(
            'id',
            'ticket_id',
            'company__name',
            'sell_currency__mnemonic',
            'buy_currency__mnemonic',
            'amount',
            'lock_side__mnemonic',
            'value_date',
            'tenor',
            'with_care',
            'time_in_force',
            'ticket_type',
            'execution_strategy',
            'broker',
            'instrument_type',
            'exec_broker',
            'spot_rate',
            'fwd_points',
            'rate',
            'fee',
            'mark_to_market',
            'last_mark_time',
            'created',
            'modified',
            named=True
        ).iterator()
        df_oems_ticket = pd.DataFrame(list(qs_oems_ticket))

        # qs_fx_forward_position = FxForwardPosition.objects.filter(
        #     created__gte=self.start_date,
        #     created__lte=self.end_date
        # ).values_list(
        #     'id',
        #     'cashflow__id',
        #     'account__company__name',
        #     'fxpair__base_currency__mnemonic',
        #     'fxpair__quote_currency__mnemonic',
        #     'amount',
        #     'delivery_time',
        #     'enter_time',
        #     'forward_price',
        #     'unwind_price',
        #     'created',
        #     'modified',
        #     named=True
        # ).iterator()
        # df_fx_forward_position = pd.DataFrame(list(qs_fx_forward_position))

        qs_spot_rate = SpotRate.objects.filter(
            created__gte=self.start_date,
            created__lte=self.end_date
        ).exclude(
            order_number__isnull=True,
            order_number__exact=None
        ).values_list(
            'id',
            'company__name',
            'fx_pair__base_currency__mnemonic',
            'fx_pair__quote_currency__mnemonic',
            'payment_currency__mnemonic',
            'payment_amount',
            'settlement_currency__mnemonic',
            'settlement_amount',
            'rate_value',
            'rate_lockside',
            'order_number',
            'created',
            'modified',
            named=True
        ).iterator()
        df_spot_rate = pd.DataFrame(list(qs_spot_rate))

        return {
            'cashflow_old': df_cashflow_old,
            'cashflow_new': df_cashflow_new,
            # 'fx_forward_position': df_fx_forward_position,
            'spot_rate': df_spot_rate,
            'oems_ticket': df_oems_ticket,
        }
