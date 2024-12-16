import logging
import traceback

from hdlib.DateTime.Date import Date
from typing import List

from main.apps.corpay.models import ManualForwardRequest
from main.apps.corpay.services.corpay import CorPayExecutionService
from main.apps.corpay.signals.handlers import new_manual_forward
from main.apps.hedge.models import DraftFxForwardPosition
from main.apps.hedge.models.fxforwardposition import FxForwardPosition

logger = logging.getLogger(__name__)


class ForwardExecutionService:
    def __init__(self, corpay_service: CorPayExecutionService):
        self._corpay_service = corpay_service

    def update_forwards(self, company):
        """
        The objective of this function is to update all the pending forwards and close the expired ones.

        It goes through the process in the following order:
        1. Get all the pending forwards
        For each pending draft forward
            1.1.1
        3. Insert FxForwardPosition objects for each forward
        :param company:
        :return:
        """
        logger.debug(f"Start updating forwards for company (ID={company.id})")
        logger.debug(f"Get all pending forwards for company (ID={company.id})")
        pending_forwards: List[DraftFxForwardPosition] = list(DraftFxForwardPosition.objects.filter(
            status=DraftFxForwardPosition.Status.PENDING_ACTIVATION,
            cashflow__account__company=company))
        logger.debug(f"Got {len(pending_forwards)} pending forwards for company (ID={company.id})")
        manual_forward_created = []

        for fwd in pending_forwards:
            try:
                logger.debug(f"Start updating forward (ID={fwd.id})")
                logger.debug(f"  - Checking that the forward has a cashflow and not just a draft cashflow")
                if fwd.cashflow is None:
                    logger.error(f"  - Forward (ID={fwd.id}) does not have a cashflow, skipping")
                    continue
                cashflows = fwd.to_hedge_cashflows(Date.today())
                logger.debug(f"  - Got {len(cashflows)} cashflows for forward (ID={fwd.id})")
                for cashflow in cashflows:
                    logger.debug(f"cashflow.currency.pk: {cashflow.currency} {cashflow.currency.pk}")
                    if ManualForwardRequest.is_manual(cashflow):
                        obj = ManualForwardRequest.create_from_cashflow(
                            pair=fwd.fxpair,
                            cashflow=cashflow,
                        )
                        manual_forward_created.append(obj)
                        logger.warning(f"Creating ManualForwardRequest record for forward (ID={fwd.id})")
                        continue

                    self._corpay_service.set_draft_fx_forward(fwd)
                    quote = self._corpay_service.execute(cashflow.currency, Date.from_datetime_date(cashflow.date),
                                                         cashflow.amount, fwd.cashflow.id)
                    logger.debug(f"Creating FxForwardPosition object for quote (ID={quote.id})")
                    pos = FxForwardPosition.objects.create(
                        cashflow=fwd.cashflow,
                        fxpair=quote.forward_quote.fx_pair,
                        amount=quote.forward_quote.amount,
                        delivery_time=quote.maturity_date,
                        enter_time=quote.forward_quote.forward_guideline.bookdate,
                        forward_price=quote.forward_quote.forward_price()
                    )
                    logger.debug(f"FxForwardPosition object created (ID={pos.id}) for quote (ID={quote.id})")
                logger.debug(f"Updating forward (ID={fwd.id}) status to ACTIVE")
                fwd.status = DraftFxForwardPosition.Status.ACTIVE
                fwd.save()
                logger.debug(f"Forward (ID={fwd.id}) updated successfully")
            except Exception as ex:
                logger.error(f"Error updating forward (ID={fwd.id}): {ex}")
                logger.error(traceback.format_exc())

        logger.debug(f"Finished updating forwards for company (ID={company.id})")
        if manual_forward_created:
            new_manual_forward.send(sender=self.__class__, company=company, instances=manual_forward_created)
