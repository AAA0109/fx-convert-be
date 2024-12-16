from rest_framework import viewsets

from main.apps.corpay.api.serializers.currency_definition import CurrencyDefinitionSerializer
from main.apps.corpay.models import CurrencyDefinition


class CurrencyDefinitionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CurrencyDefinition.objects.all()
    serializer_class = CurrencyDefinitionSerializer
    filterset_fields = ['p10', 'wallet', 'wallet_api', 'ndf', 'fwd_delivery_buying', 'fwd_delivery_selling', 'outgoing_payments', 'incoming_payments']
