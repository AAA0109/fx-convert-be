from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny

from main.apps.account.api.serializers.support import SendAuthenticatedSupportMessageSerializer, \
    SendGeneralSupportMessageSerializer
from main.apps.core.serializers.action_status_serializer import ActionStatusSerializer
from main.apps.core.utils.api import get_response_from_action_status
from main.apps.util import ActionStatus


@extend_schema(
    request=SendAuthenticatedSupportMessageSerializer,
    responses={
        status.HTTP_200_OK: ActionStatusSerializer,
        status.HTTP_400_BAD_REQUEST: ActionStatusSerializer,
        status.HTTP_500_INTERNAL_SERVER_ERROR: ActionStatusSerializer
    }
)
class SendAuthenticatedSupportMessageView(generics.CreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SendAuthenticatedSupportMessageSerializer

    def create(self, request, *args, **kwargs):

        try:
            context = {
                "user": request.user
            }
            serializer = self.serializer_class(data=request.data, context=context)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        except ValidationError as e:
            return get_response_from_action_status(action_status=ActionStatus(status=ActionStatus.Status.ERROR,
                                                                              message=str(e)),
                                                   http_status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return get_response_from_action_status(action_status=ActionStatus(status=ActionStatus.Status.ERROR,
                                                                              message=str(e)),
                                                   http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return get_response_from_action_status(action_status=ActionStatus(status=ActionStatus.Status.SUCCESS,
                                                                          message="Success"),
                                               http_status=status.HTTP_200_OK)


@extend_schema(
    request=SendGeneralSupportMessageSerializer,
    responses={
        status.HTTP_200_OK: ActionStatusSerializer,
        status.HTTP_400_BAD_REQUEST: ActionStatusSerializer,
        status.HTTP_500_INTERNAL_SERVER_ERROR: ActionStatusSerializer
    }
)
class SendGeneralSupportMessageView(generics.CreateAPIView):
    serializer_class = SendGeneralSupportMessageSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        except ValidationError as e:
            return get_response_from_action_status(action_status=ActionStatus(status=ActionStatus.Status.ERROR,
                                                                              message=str(e)),
                                                   http_status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return get_response_from_action_status(action_status=ActionStatus(status=ActionStatus.Status.ERROR,
                                                                              message=str(e)),
                                                   http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return get_response_from_action_status(action_status=ActionStatus(status=ActionStatus.Status.SUCCESS,
                                                                          message="Success"),
                                               http_status=status.HTTP_200_OK)
