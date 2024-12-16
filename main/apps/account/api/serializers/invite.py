from drf_simple_invite.serializers import InviteEmailSerializer
from drf_simple_invite.models import InvitationToken
from drf_simple_invite.serializers import PasswordSerializer
from rest_framework import serializers

from main.apps.account.models import User


class InviteResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class ExtendInviteSerializer(InviteEmailSerializer):
    group = serializers.ChoiceField(choices=User.UserGroups.choices, default=User.UserGroups.CUSTOMER_VIEWER)


class InviteTokenSerializer(serializers.Serializer):
    invitation_token = serializers.CharField()


class InviteTokenResponseSerializer(serializers.Serializer):
    email = serializers.CharField()


class InviteTokenErrorSerializer(serializers.Serializer):
    error = serializers.CharField()


class SetUserPasswordSerializer(PasswordSerializer):
    firstName = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    lastName = serializers.CharField(required=False, allow_null=True, allow_blank=True)
