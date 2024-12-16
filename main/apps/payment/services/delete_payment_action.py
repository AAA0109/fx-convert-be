from rest_framework import status
from typing import List, Optional
from main.apps.cashflow.models.cashflow import SingleCashFlow
from main.apps.oems.services.trading import trading_provider
from main.apps.payment.models import Payment


class DeletePaymentAction:
    payment:Payment
    ticket_ids:List[str] = []

    def __init__(self, payment:Payment) -> None:
        self.payment = payment
        self.ticket_ids = self._populate_ticket_ids()

    def _populate_ticket_ids(self) -> List[str]:
        ticket_ids = []
        cashflows = SingleCashFlow.objects.filter(generator=self.payment.cashflow_generator)
        for cashflow in cashflows:
            if cashflow.ticket_id:
                ticket_ids.append(cashflow.ticket_id.__str__())
        return ticket_ids

    def cancel_ticket(self) -> Optional[List[dict]]:
        if len(self.ticket_ids) == 0:
            return None

        payloads = []
        for ticket_id in self.ticket_ids:
            payloads.append({
                'ticket_id': ticket_id
            })

        responses = trading_provider.req_cancel(request=payloads)

        cancel_success = []
        cancel_failed = []
        cancel_resp = responses.data

        for i in range(len(cancel_resp)):
            if cancel_resp[i]['status'] in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED]:
                cancel_success.append({
                    'ticket_id': self.ticket_ids[i],
                    'data': cancel_resp[i]['data'],
                    'status': cancel_resp[i]['status']
                })
                continue
            cancel_failed.append({
                'ticket_id': self.ticket_ids[i],
                'data': cancel_resp[i]['data'],
                'status': cancel_resp[i]['status']
            })
        return {
            'success': cancel_success,
            'failed': cancel_failed
        }
