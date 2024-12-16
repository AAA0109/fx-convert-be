from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated

from main.apps.webhook.models.webhook import Webhook, Event, EventGroup
from main.apps.webhook.api.serializers.webhook import WebhookSerializer, EventSerializer, \
    EventGroupSerializer


class WebhookViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = WebhookSerializer
    lookup_field = 'webhook_id'

    def get_queryset(self):
        return Webhook.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user)

    @extend_schema(
        tags=["Webhook"],
        summary="Create a new webhook",
        description="Endpoint for creating a new webhook associated with the current user's company.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        tags=["Webhook"],
        summary="Retrieve a webhook",
        description="Endpoint for retrieving details of a specific webhook.",
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=["Webhook"],
        summary="List webhooks",
        description="Endpoint for retrieving a list of all webhooks for the current user's company.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=["Webhook"],
        summary="Replace a webhook",
        description="Endpoint for replacing an existing webhook.",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        tags=["Webhook"],
        summary="Partially update a webhook",
        description="Endpoint for partially updating an existing webhook.",
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        tags=["Webhook"],
        summary="Delete a webhook",
        description="Endpoint for deleting an existing webhook.",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


@extend_schema(
    tags=['Webhook'],
    summary='List all webhook events',
    description='Retrieve a list of all available webhook events.'
)
class WebhookEventListView(generics.ListAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer


@extend_schema(
    tags=['Webhook'],
    summary='List all webhook event groups',
    description='Retrieve a list of all available webhook event groups.'
)
class WebhookEventGroupListView(generics.ListAPIView):
    queryset = EventGroup.objects.all()
    serializer_class = EventGroupSerializer
