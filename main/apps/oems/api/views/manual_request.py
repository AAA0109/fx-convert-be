from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from main.apps.oems.api.serializers.manual_request import ManualRequestSerializer
from main.apps.oems.models import ManualRequest


class ManualRequestViewSet(mixins.CreateModelMixin,
                           mixins.UpdateModelMixin,
                           mixins.DestroyModelMixin,
                           GenericViewSet):
    queryset = ManualRequest.objects.all()
    serializer_class = ManualRequestSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        instance = serializer.save()

        # @todo call send_slack_form and update slack_ts
        instance.slack_ts = '123'
        instance.save()
        return instance

    def perform_update(self, serializer):
        # @todo call edit_slack_form
        instance = serializer.save()
        return instance

    def perform_destroy(self, instance):
        # @todo call delete_slack_form
        super().perform_destroy(instance)
