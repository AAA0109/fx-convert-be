from rest_framework import serializers
from django_bulk_load import bulk_upsert_models

from main.apps.notification.models import NotificationEvent, UserNotification
from main.apps.notification.services.email.templates import EMAIL_TEMPLATES


class NotificationEventSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='get_type_display')

    class Meta:
        model = NotificationEvent
        fields = '__all__'


class UserNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotification
        fields = '__all__'


class UserNotificationBulkCreateUpdateSerializer(serializers.Serializer):
    email = serializers.BooleanField()
    sms = serializers.BooleanField()
    phone = serializers.BooleanField()
    user = serializers.IntegerField()
    event = serializers.IntegerField()


class UserNotificationBulkUpdateListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        return self._bulk_upsert_model_from_validated_date(validated_data)

    def update(self, instances, validated_data):
        return self._bulk_upsert_model_from_validated_date(validated_data)

    def validate(self, data):
        for user_notification in data:
            if user_notification['user'].id != self.context['user'].id:
                raise serializers.ValidationError("User does not match authenticated user")
        return data

    def _get_models_from_validated_date(self, validated_data):
        models = []
        for user_notification in validated_data:
            models.append(UserNotification(
                email=user_notification['email'],
                sms=user_notification['sms'],
                phone=user_notification['phone'],
                user_id=user_notification['user'].id,
                event_id=user_notification['event'].id
            ))
        return models

    def _bulk_upsert_model_from_validated_date(self, validated_data):
        models = self._get_models_from_validated_date(validated_data)
        created_models = bulk_upsert_models(models=models, pk_field_names=self._get_models_pk_field(),
                                            return_models=True)
        return created_models

    def _get_models_pk_field(self):
        return [
            'user_id', 'event_id'
        ]


class ResendNotificationRequestSerializer(serializers.Serializer):
    template = serializers.ChoiceField(choices=EMAIL_TEMPLATES)
    email = serializers.EmailField()


class ResendNotificationResponseSerializer(serializers.Serializer):
    details = serializers.CharField()
