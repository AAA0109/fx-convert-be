from drf_spectacular.utils import extend_schema
from rest_framework import status, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet

from main.apps.notification.api.serializers.notification import NotificationEventSerializer, \
    UserNotificationSerializer, UserNotificationBulkUpdateListSerializer, UserNotificationBulkCreateUpdateSerializer, \
    ResendNotificationRequestSerializer, ResendNotificationResponseSerializer
from main.apps.notification.models import NotificationEvent, UserNotification
from main.apps.notification.utils.email import resend_email_template


class NotificationEventViewSet(ReadOnlyModelViewSet):
    queryset = NotificationEvent.objects.all()
    serializer_class = NotificationEventSerializer


class UserNotificationViewSet(ModelViewSet):
    queryset = UserNotification.objects.all()
    serializer_class = UserNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return UserNotification.objects.filter(user=user)

    @extend_schema(
        request=UserNotificationBulkUpdateListSerializer(child=UserNotificationBulkCreateUpdateSerializer()),
        responses={
            status.HTTP_200_OK: UserNotificationBulkUpdateListSerializer(
                child=UserNotificationBulkCreateUpdateSerializer()),
            status.HTTP_400_BAD_REQUEST: serializers.ValidationError
        }
    )
    @action(detail=False, methods=['put'], pagination_class=None, filter_backends=[])
    def bulk_create_update(self, request):
        serializer = UserNotificationBulkUpdateListSerializer(context={"user": request.user},
                                                              child=UserNotificationSerializer(), data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        data = serializer.data
        return Response(data)


class ResendNotificationView(APIView):

    @extend_schema(
        request=ResendNotificationRequestSerializer,
        responses={
            status.HTTP_200_OK: ResendNotificationResponseSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = ResendNotificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template = serializer.validated_data.get('template')
        email = serializer.validated_data.get('email')
        if not resend_email_template(template=template, email=email):
            return Response({
                "detail": "Unable to resend email, please check your request"
            }, status.HTTP_400_BAD_REQUEST)
        return Response({
            "detail": "success"
        }, status.HTTP_200_OK)
