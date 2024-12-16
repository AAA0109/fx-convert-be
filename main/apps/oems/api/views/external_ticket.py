from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from rest_framework import mixins, viewsets, filters, status

from main.apps.oems.models import Ticket

from rest_framework.permissions import IsAuthenticated
from main.apps.core.utils.api import HasCompanyAssociated, UserBelongsToCompany

from rest_framework import serializers

from main.apps.account.models import Company
from main.apps.currency.models import Currency
from main.apps.core.constants import CURRENCY_HELP_TEXT, LOCK_SIDE_HELP_TEXT
from main.apps.oems.api.utils.response import *

# ===========

class ExternalTicketSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ticket
        # These are the fields we want to expose publicly via the API
        fields = [
            'ticket_id',
            'company',
            'customer_id',
            'sell_currency',
            'buy_currency',
            'amount',
            'lock_side',
            'value_date',
            'draft',
            'with_care',
            'transaction_id',
            'transaction_group',
            'start_time',
            'end_time',
            'execution_strategy',
            'broker',
            'upper_trigger',
            'lower_trigger',
            'auth_user',
        ]

class ExternalMtmSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ticket
        # These are the fields we want to expose publicly via the API
        fields = [
            'ticket_id',
            'company',
            'customer_id',
            'sell_currency',
            'buy_currency',
            'amount',
            'lock_side',
            'value_date',
            'transaction_id',
            'transaction_group',
            'mark_to_market',
            'last_mark_time',
            'mtm_info',
        ]

# ===========

class CustomSearchFilter(filters.SearchFilter):
    def get_search_fields(self, view, request):
        #if request.query_params.get('title_only'):
        #    return ['title']
        return super().get_search_fields(view, request)

# ===========

class ExternalTicketViewSet(mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    queryset = Ticket.objects.all()
    serializer_class = ExternalTicketSerializer
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    filter_backends = [CustomSearchFilter]
    search_fields = ['=ticket_id', '=buy_currency','=sell_currency','created','external_state'] # trader, auth_user, etc.
    # ordering_fields = ['create_time']
    ordering = ['created']

    def get_queryset(self):
        """
        This view should return a list of all the records
        for the currently authenticated user.
        """
        user = self.request.user
        # assume power user for now
        return self.queryset.filter(company=user.company.pk)

    @extend_schema(
        summary="List Executions",
        description="Endpoint to retrieve executed transaction details.",
        tags=['Trading'],
        responses={
            400: EXTERNAL_PANGEA_400,
            401: EXTERNAL_PANGEA_401,
            403: EXTERNAL_PANGEA_403,
            404: EXTERNAL_PANGEA_404,
            406: EXTERNAL_PANGEA_406,
            status.HTTP_200_OK: OpenApiTypes.OBJECT,
        },
    )
    def list(self, request, *args, **kwargs):
        # company = request.user.company.pk
        # user = request.user.id
        # what executions can user see?
        # can definitely only see executions from the company
        return super().list(request, *args, **kwargs)


class ExternalMtmViewSet(mixins.RetrieveModelMixin,
                    viewsets.GenericViewSet):
    queryset = Ticket.objects.all()
    serializer_class = ExternalMtmSerializer
    lookup_field = "ticket_id"

    @extend_schema(
        summary="Mark-to-Market",
        description="Endpoint for retrieving a specific ticket mark-to-market by its ticket id.",
        tags=['Trading'],
        responses={
            400: EXTERNAL_PANGEA_400,
            401: EXTERNAL_PANGEA_401,
            403: EXTERNAL_PANGEA_403,
            404: EXTERNAL_PANGEA_404,
            406: EXTERNAL_PANGEA_406,
            status.HTTP_200_OK: ExternalMtmSerializer,
        },
    )

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)




