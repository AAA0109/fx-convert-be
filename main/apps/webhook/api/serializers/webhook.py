from rest_framework import serializers

from main.apps.account.models import User
from main.apps.webhook.models import Webhook, Event, EventGroup


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ('name', 'type')


class EventGroupSerializer(serializers.ModelSerializer):
    events = EventSerializer(many=True, read_only=True)

    class Meta:
        model = EventGroup
        fields = ('name', 'slug', 'events')


class WebhookSerializer(serializers.ModelSerializer):
    events = serializers.SlugRelatedField(
        many=True, queryset=Event.objects.all(), slug_field='type'
    )
    groups = serializers.SlugRelatedField(
        many=True, queryset=EventGroup.objects.all(), slug_field='slug'
    )
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Webhook
        fields = ('webhook_id', 'created_by', 'url', 'events', 'groups', 'created', 'modified')
