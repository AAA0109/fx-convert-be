import abc
from typing import Iterable

from django.db.models import Q

from main.apps.hedge.models import DraftFxForwardPosition


class FxForwardService(abc.ABC):

    def create_unexecuted_forward(self,
                                  status,
                                  cashflow_id,
                                  draft_id,
                                  risk_reduction,
                                  fxpair,
                                  delivery_time) -> DraftFxForwardPosition:
        """
        Creates an unexecuted forward.
        :param status:
        :param cashflow_id:
        :param draft_id:
        :param risk_reduction:
        :param fxpair:
        :param delivery_time:
        :return:
        """
        ...

    def get_company_unexecuted_forwards(self, company_id,
                                        status=DraftFxForwardPosition.Status.PENDING_ACTIVATION):
        """
        Gets all unexecuted forwards for a company.
        :param company_id:
        :return:
        """
        ...



class CorPayFxForwardService(FxForwardService):
    def create_unexecuted_forward(self,
                                  status,
                                  cashflow_id,
                                  draft_id,
                                  risk_reduction,
                                  fxpair,
                                  delivery_time) -> DraftFxForwardPosition:
        return DraftFxForwardPosition.objects.create(
            status=status,
            cashflow_id=cashflow_id,
            draft_id=draft_id,
            risk_reduction=risk_reduction,
            fxpair=fxpair,
            delivery_time=delivery_time
        )

    def get_company_unexecuted_forwards(
        self,
        company,
        status=DraftFxForwardPosition.Status.PENDING_ACTIVATION) -> Iterable[DraftFxForwardPosition]:
        query = (Q(cashflow__account__company=company) | Q(draft__ompany=company)) & Q(status=status)
        return DraftFxForwardPosition.objects.filter(query)
