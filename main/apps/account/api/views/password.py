from drf_spectacular.utils import extend_schema

from rest_framework import status, mixins
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated

from main.apps.account.models.user import User
from main.apps.account.api.serializers.password import ChangePasswordSerializer
from main.apps.core.serializers.action_status_serializer import ActionStatusSerializer
from main.apps.core.utils.api import get_response_from_action_status
from main.apps.util import ActionStatus


class ChangePasswordView(mixins.UpdateModelMixin, GenericAPIView):
    serializer_class = ChangePasswordSerializer
    model = User
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        obj = self.request.user
        return obj

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={
            status.HTTP_200_OK: ActionStatusSerializer,
            status.HTTP_400_BAD_REQUEST: ActionStatusSerializer
        }
    )
    def put(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            if not self.object.check_password(serializer.data.get('old_password')):
                return get_response_from_action_status(
                    data={"old_password": ["Wrong password"]},
                    http_status=status.HTTP_400_BAD_REQUEST,
                    action_status=ActionStatus(
                        message="Error: Bad Request",
                        status=ActionStatus.Status.ERROR
                    )
                )
            # set_password also hashes the password that the user will get
            self.object.set_password(serializer.data.get("new_password"))
            self.object.save()
            return get_response_from_action_status(
                data={},
                http_status=status.HTTP_200_OK,
                action_status=ActionStatus(
                    message="Success",
                    status=ActionStatus.Status.SUCCESS
                )
            )

        return get_response_from_action_status(
            data=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST,
            action_status=ActionStatus(
                message="Error; Bad Request",
                status=ActionStatus.Status.ERROR
            )
        )
