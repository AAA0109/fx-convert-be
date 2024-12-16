import rest_framework.fields
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, status
from rest_framework.fields import CharField
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer

from main.apps.account.models import Company
from main.apps.currency.models import FxPair
from main.apps.oems.models import CnyExecution


# Create your views here.


class CnyExecutionSerializer(ModelSerializer):
    market = CharField(source='fxpair.market')
    subaccounts = rest_framework.fields.ListField(source='broker_accounts', child=CharField())

    class Meta:
        model = CnyExecution
        exclude = ('fxpair',)


class CnyExecutionView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    queryset = CnyExecution.objects.all()

    @extend_schema(
        parameters=[
            OpenApiParameter(name='market',
                             location=OpenApiParameter.QUERY,
                             description='Query a specific market',
                             type=OpenApiTypes.STR,
                             required=False),
            OpenApiParameter(name='company',
                             location=OpenApiParameter.QUERY,
                             description='Query a specific broker account',
                             type=OpenApiTypes.INT,
                             required=True),
        ],
        responses={
            status.HTTP_200_OK: CnyExecutionSerializer(many=True)
        }
    )
    def list(self, request):
        """
        Get all the cashflows for an account
        """

        company_id = int(request.query_params.get('company'))
        company = Company.get_company(company_id)
        market = request.query_params.get('market', None)
        fxpair = FxPair.get_pair(market)
        cny_execution = get_object_or_404(self.queryset, company=company, fxpair=fxpair)
        
        serializer = CnyExecutionSerializer(cny_execution, many=False)
        return Response(serializer.data)
