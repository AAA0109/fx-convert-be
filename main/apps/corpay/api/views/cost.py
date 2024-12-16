from drf_spectacular.utils import extend_schema
from rest_framework import views, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from main.apps.corpay.api.serializers.cost.currency import CostRequestSerializer, CostResponseSerializer
from main.apps.corpay.models import TransactionCost, AumCost


class RetrieveCostView(views.APIView):
    serializer_class = CostRequestSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[CostRequestSerializer],
        responses={
            status.HTTP_200_OK: CostResponseSerializer
        }
    )
    def get(self, request):
        serializer = CostRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        aum = serializer.validated_data.get('aum')
        transaction_costs = TransactionCost.objects.filter(
            average_volume_low__lte=aum,
            average_volume_high__gt=aum
        ).order_by(
            'currency_category',
            'notional_low'
        )
        transactions = {}
        for transaction_cost in transaction_costs:
            key = f"{transaction_cost.notional_low}|{transaction_cost.notional_high}"
            if not key in  transactions:
                transactions[key] = {
                    "transaction_low": transaction_cost.notional_low,
                    "transaction_high": transaction_cost.notional_high,
                    "wire": "free"
                }
            if transaction_cost.currency_category == 'p10':
                transactions[key]['p10'] = transaction_cost.cost_in_bps
            if transaction_cost.currency_category == 'other':
                transactions[key]['other'] = transaction_cost.cost_in_bps
        transactions = transactions.values()
        aum_cost = AumCost.objects.filter(average_volume_low__lte=aum, average_volume_high__gt=aum).first()
        aum = {
            "annualized_rate": aum_cost.annualized_rate,
            "minimum_rate": aum_cost.minimum_rate
        }
        response_serializer = CostResponseSerializer({
            "transactions": transactions,
            "aum": aum
        })

        return Response(response_serializer.data, status.HTTP_200_OK)



