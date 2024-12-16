from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets

from main.apps.oems.api.serializers.ticket import TicketSerializer
from main.apps.oems.models import Ticket

from idempotency_key.decorators import idempotency_key

# TODO: add company + customer permissioning
# from rest_framework.permissions import IsAuthenticated, HasCompanyAssociated?

class TicketViewSet(mixins.CreateModelMixin,
                    mixins.RetrieveModelMixin,
                    mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

    @extend_schema(
        description="Endpoint for creating a new payment ticket. Allows clients to create a new payment request.",
        #examples=[{}], # TODO
    )
    @idempotency_key(optional=True)
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        description="Endpoint for retrieving a list of all payment tickets. Allows clients to retrieve all existing payment tickets."
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        description="Endpoint for retrieving a specific payment ticket by its unique ID."
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
