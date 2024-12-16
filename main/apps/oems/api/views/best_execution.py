import logging
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from main.apps.oems.api.serializers.best_execution import BestExecutionTimingSerializer
from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.oems.services.se.execution_option import ExecutionOptionProvider
from main.apps.payment.models.payment import Payment


logger = logging.getLogger(__name__)


class BestExecutionTimingAPIView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        responses={
            status.HTTP_200_OK: BestExecutionTimingSerializer
        }
    )
    def get(self, request, payment_id:int):

        try:
            payment = Payment.objects.get(pk=payment_id)
        except Payment.DoesNotExist as e:
            return Response({"message":str(e)}, status.HTTP_404_NOT_FOUND)

        try:
            exec_provider = ExecutionOptionProvider(payment=payment)
            response = exec_provider.get_execution_options()
            response_serializer = BestExecutionTimingSerializer(response)
            return Response(response_serializer.data, status.HTTP_200_OK)
        except Exception as e:
            logger.error(str(e), exc_info=True)
            return Response({"message": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)
