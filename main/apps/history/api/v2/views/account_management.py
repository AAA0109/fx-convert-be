import logging
from typing import Type

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from main.apps.billing.models import Fee
from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.hedge.models import FxPosition
from main.apps.history.api.v2.serializers.account_management import (
    FeesPaymentsSerializer,
    FeeFilter, BankStatementSerializer, BankStatementFilter, TradeSerializer, TradeFilter,
    ActivitySerializer, ActivityFilter, ActivitiesSerializer
)
from main.apps.history.models.account_management import UserActivity
from main.apps.ibkr.models import DepositResult

logger = logging.getLogger(__name__)

class ActivitiesView(viewsets.ReadOnlyModelViewSet):

    permission_classes = [IsAuthenticated]
    filter_class = ActivityFilter

    def get_serializer_class(self) -> Type[ActivitySerializer]:
        return ActivitySerializer
    def get_queryset(self):
        try:
            if self.request.user.id:
                entries = UserActivity.get_query_set(self.request.user)
                return entries
            else:
                return UserActivity.objects.none()
        except Exception as e:
            logger.error(e)
            return UserActivity.objects.none()


class FeesPaymentsView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    serializer_class = FeesPaymentsSerializer
    filter_class = FeeFilter

    def get_queryset(self):
        return Fee.objects.filter(company=self.request.user.company, amount__gt=0).order_by('-incurred')



class BankStatementsView(viewsets.ReadOnlyModelViewSet):
    serializer_class = BankStatementSerializer
    filter_class = BankStatementFilter
    permission_classes = (IsAuthenticated, HasCompanyAssociated)

    def get_queryset(self):
        return DepositResult.objects.filter(funding_request__broker_account__company=self.request.user.company).order_by('-created')




class TradesView(viewsets.ReadOnlyModelViewSet):
    serializer_class = TradeSerializer
    filter_class = TradeFilter
    permission_classes = (IsAuthenticated, HasCompanyAssociated)

    def get_queryset(self):
        return FxPosition.objects.filter(account__company=self.request.user.company).order_by('-company_event__time')


