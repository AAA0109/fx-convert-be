import base64
import logging
import uuid

from drf_simple_invite.models import InvitationToken
from drf_simple_invite.signals import invitation_token_created
from drf_simple_invite.views import InviteUserView, SetUserPasswordView
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from main.apps.account.api.serializers.invite import (
    SetUserPasswordSerializer,
    InviteResponseSerializer,
    ExtendInviteSerializer,
    InviteTokenErrorSerializer,
    InviteTokenResponseSerializer,
    InviteTokenSerializer
)
from main.apps.account.api.services.customer import CustomerAPIService
from main.apps.account.models.user import User
from main.apps.core.utils.api import HasCompanyAssociated


logger = logging.getLogger(__name__)


@extend_schema(
    request=SetUserPasswordSerializer,
    responses={
        status.HTTP_200_OK: InviteResponseSerializer
    }
)
class ExtendSetUserPasswordView(SetUserPasswordView):

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(
    request=ExtendInviteSerializer,
    responses={
        status.HTTP_200_OK: InviteResponseSerializer
    }
)
class ExtendInviteUserView(InviteUserView):
    permission_classes = (IsAuthenticated, HasCompanyAssociated)
    serializer_class = ExtendInviteSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = request.data['email']
        try:
            user = User.objects.get(email=email)
            if user.id is not None and user.is_active is False:
                raise serializers.ValidationError({"detail": "User pending account activation"})
            if user.is_active:
                raise serializers.ValidationError({'detail': 'Cannot Invite Active User'})
            if user.id:
                raise serializers.ValidationError({"detail": "User already exist"})
        except User.DoesNotExist:
            user = User(email=email, is_active=False, company=request.user.company, is_invited=True)
            user.save()
        try:
            invitation_token = InvitationToken.objects.get(user=user)
        except InvitationToken.DoesNotExist:
            invitation_token = InvitationToken.objects.create(user=user)
        invitation_token.extend.inviter = request.user
        invitation_token.extend.save()
        CustomerAPIService().update_user_group(user, serializer.validated_data.get('group'))
        encoded = base64.urlsafe_b64encode(str(invitation_token.id).encode()).decode()
        invitation_token_created.send(sender=user.__class__, instance=invitation_token, invitation_token=encoded,
                                      user=user, inviter=invitation_token.extend.inviter)
        return Response({'detail': 'User Invited Successfully'}, status=status.HTTP_200_OK)


@extend_schema(
    parameters=[InviteTokenSerializer],
    responses={
        status.HTTP_200_OK: InviteTokenResponseSerializer,
        status.HTTP_400_BAD_REQUEST: InviteTokenErrorSerializer,
        status.HTTP_500_INTERNAL_SERVER_ERROR: InviteTokenErrorSerializer,
    }
)
class InviteUserTokenView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        serializer = InviteTokenSerializer(data=request.query_params)

        invalid_token_error = InviteTokenErrorSerializer({'error': 'Invalid invitation token'})
        serializer.is_valid(raise_exception=True)

        try:
            encoded = serializer.validated_data.get('invitation_token')
            decoded = base64.urlsafe_b64decode(encoded).decode()
            token_uuid = uuid.UUID(str(decoded))
            invite_token = InvitationToken.objects.get(id=decoded)
            resp_serializer = InviteTokenResponseSerializer({'email': invite_token.user.email})
            return Response(resp_serializer.data, status=status.HTTP_200_OK)
        except UnicodeDecodeError:
            return Response(invalid_token_error.data, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response(invalid_token_error.data, status=status.HTTP_400_BAD_REQUEST)
        except InvitationToken.DoesNotExist:
            return Response(invalid_token_error.data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(str(e), exc_info=True)
            error_serializer = InviteTokenErrorSerializer(data={'error':str(e)})
            return Response(error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
