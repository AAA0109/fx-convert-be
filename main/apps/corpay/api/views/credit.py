import logging

from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated

from main.apps.core.utils.api import *

logger = logging.getLogger(__name__)
from rest_framework import serializers

from main.apps.corpay.services.credit_utilization import CorPayCreditUtilizationService

service = CorPayCreditUtilizationService()


class CreditUtilizationSerializer(serializers.Serializer):
    credit_utilization = serializers.FloatField()
    credit_limit = serializers.FloatField()
    forward_pnl = serializers.FloatField()


@extend_schema(
    responses={
        status.HTTP_200_OK: CreditUtilizationSerializer
    }
)
class CreditUtilizationViewset(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    serializers = CreditUtilizationSerializer

    def list(self, request):
        utilization = service.get_credit_utilization(request.user.company)

        serializer = CreditUtilizationSerializer({
            "credit_utilization": utilization.credit_utilization,
            "credit_limit": utilization.credit_limit,
            "forward_pnl": utilization.forward_pnl,
        })

        return Response(serializer.data)
