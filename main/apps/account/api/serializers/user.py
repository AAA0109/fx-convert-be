import pytz
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers, status
from rest_framework.validators import UniqueValidator

from main.apps.account.api.serializers.company import CompanySerializer
from main.apps.account.models.user import User
from main.apps.core.serializers.fields.timezone import TimeZoneSerializerChoiceField


# ====================================================================
#  User serializers
# ====================================================================
class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = [
            'name',
            'content_type',
            'codename'
        ]


class GroupSerializer(serializers.ModelSerializer):
    name = serializers.ChoiceField(choices=User.UserGroups.choices)
    permissions = PermissionSerializer(many=True)

    class Meta:
        model = Group
        fields = [
            'name',
            'permissions'
        ]


class UserSerializer(serializers.ModelSerializer):
    company = CompanySerializer()
    first_name = serializers.CharField(required=True)
    phone = PhoneNumberField(required=False)
    timezone = TimeZoneSerializerChoiceField(use_pytz=True)
    groups = GroupSerializer(many=True)
    can_bypass_approval = serializers.BooleanField(required=False,
                                                   allow_null=True)

    class Meta:
        model = User
        fields = [
            'id',
            # 'username', Removed the fields
            'first_name',
            'last_name',
            # 'last_login',
            'email',
            'is_active',
            # 'date_joined',
            'phone',
            'phone_confirmed',
            'company',
            'timezone',
            'groups',
            'can_bypass_approval'
        ]

        read_only_fields = [
            'can_bypass_approval',
        ]


class UserCreationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True, required=True)
    phone = PhoneNumberField(required=False)
    timezone = TimeZoneSerializerChoiceField(use_pytz=True)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone', 'timezone', 'password', 'confirm_password',)

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})

        return attrs


class UserUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=False,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    phone = PhoneNumberField(required=False)
    timezone = TimeZoneSerializerChoiceField(use_pytz=True, required=False, allow_blank=True, default=pytz.UTC)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone', 'timezone']

    def validate(self, attrs):
        if ('password' in attrs and 'confirm_password' in attrs) and (attrs['password'] != attrs['confirm_password']):
            raise serializers.ValidationError({"password": "Password fields didn't match."})

        return attrs


class ActivateUserRequestSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=60, required=True)


class ActivateUserResponseSerializer(serializers.Serializer):
    status = serializers.BooleanField()
    message = serializers.CharField(required=False)


class UserEmailExistsRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class UserEmailExistsResponseSerializer(serializers.Serializer):
    exists = serializers.BooleanField()
    is_active = serializers.BooleanField(required=False)

class UserConfirmPhoneSerializer(serializers.Serializer):
    phone = PhoneNumberField()


class UserVerifyPhoneOTPSerializer(serializers.Serializer):
    otp_code = serializers.CharField(max_length=6)


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name='Success response',
            value={
                'status': True
            },
            status_codes=[status.HTTP_200_OK]
        ),
        OpenApiExample(
            name='Error response',
            value={
                'status': False,
                'error': 'Some error message'
            },
            status_codes=[status.HTTP_400_BAD_REQUEST,
                          status.HTTP_500_INTERNAL_SERVER_ERROR]
        ),
    ]
)
class StatusResponseSerializer(serializers.Serializer):
    status = serializers.BooleanField()
    error = serializers.CharField(required=False)


class UpdateUserPermissionGroupSerializer(serializers.Serializer):
    group = serializers.ChoiceField(choices=User.UserGroups.choices, default=User.UserGroups.CUSTOMER_VIEWER)
