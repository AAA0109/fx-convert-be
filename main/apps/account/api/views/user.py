from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets, generics
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from main.apps.account.api.serializers.user import *
from main.apps.account.api.services.customer import CustomerAPIService
from main.apps.account.models import User
from main.apps.account.permissions.user import UserIsAdmin, UserInSameCompany
from main.apps.account.services.user import UserService
from main.apps.approval.services.payment_approval import PaymentApprovalService
# ====================================================================
#  User
# ====================================================================
from main.apps.core.serializers.resource_exists_serializer import ResourceAlreadyExists


class UserViewSet(viewsets.ViewSet):
    queryset = User.objects.all()

    def get_permissions(self):
        if self.request.method == 'POST':
            self.permission_classes = [AllowAny]
        else:
            self.permission_classes = [IsAuthenticated]

        return super(UserViewSet, self).get_permissions()

    @extend_schema(responses={
        status.HTTP_200_OK: UserSerializer
    })
    def list(self, request):
        """
        Get current user
        """
        approval_svc = PaymentApprovalService(company=request.user.company)
        request.user.can_bypass_approval = approval_svc.can_bypass_approval(user=request.user)
        serializer = UserSerializer(request.user)
        return Response([serializer.data])

    @extend_schema(
        request=UserCreationSerializer,
        responses={
            status.HTTP_201_CREATED: UserSerializer,
            status.HTTP_409_CONFLICT: ResourceAlreadyExists
        }
    )
    def create(self, request):
        """
        Create new user
        """
        serializer = UserCreationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = CustomerAPIService().create_user(email=serializer.validated_data.get('email').lower(),
                                                    first_name=serializer.validated_data.get('first_name'),
                                                    last_name=serializer.validated_data.get('last_name'),
                                                    password=serializer.validated_data.get('password'),
                                                    phone=serializer.validated_data.get('phone'),
                                                    timezone=serializer.validated_data.get('timezone'))
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        except User.AlreadyExists as e:
            return Response({
                'message': str(e),
                'field': "name"
            }, status.HTTP_409_CONFLICT)

    @extend_schema(
        request=UserUpdateSerializer,
        responses={
            status.HTTP_200_OK: UserSerializer,
            status.HTTP_409_CONFLICT: ResourceAlreadyExists
        }
    )
    def update(self, request, pk=None):
        """
        Edit current user
        """
        user = request.user
        request_data = request.data
        if not hasattr(request_data, 'timezone'):
            request_data['timezone'] = pytz.UTC
        serializer = UserUpdateSerializer(user, data=request_data)
        serializer.is_valid(raise_exception=True)
        try:
            user = CustomerAPIService().update_user(user_id=user.id,
                                                    first_name=serializer.validated_data.get('first_name'),
                                                    last_name=serializer.validated_data.get('last_name'),
                                                    email=serializer.validated_data.get('email'),
                                                    phone=serializer.validated_data.get('phone'),
                                                    timezone=serializer.validated_data.get('timezone'))

            serializer = UserSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except User.AlreadyExists as e:
            return Response({
                'message': e.message,
                'field': "name"
            }, status.HTTP_409_CONFLICT)

    @extend_schema(
        request=UserUpdateSerializer,
        responses={
            status.HTTP_200_OK: UserSerializer,
            status.HTTP_409_CONFLICT: ResourceAlreadyExists
        }
    )
    def partial_update(self, request, pk=None):
        return self.update(request, pk)


class ActivateUserView(generics.RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ActivateUserRequestSerializer
    queryset = User.objects.all()
    lookup_url_kwarg = 'id'

    @extend_schema(
        parameters=[ActivateUserRequestSerializer],
        responses={
            status.HTTP_200_OK: ActivateUserResponseSerializer,
            status.HTTP_400_BAD_REQUEST: ActivateUserResponseSerializer
        }
    )
    def get(self, request: Request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)

        try:
            serializer.is_valid(raise_exception=True)
            token = serializer.validated_data.get('token')
            user = get_object_or_404(self.queryset, activation_token=token)
            if not CustomerAPIService().activate_user(user=user, activation_token=token):
                raise ValidationError('Unable to activate user')
            return Response({"status": True}, status.HTTP_200_OK)
        except Exception as e:
            return Response({"status": False, "message": e}, status.HTTP_400_BAD_REQUEST)


class UserEmailExistsView(generics.RetrieveAPIView):
    serializer_class = UserEmailExistsRequestSerializer
    queryset = User.objects.all()

    @extend_schema(
        parameters=[UserEmailExistsRequestSerializer],
        responses={
            status.HTTP_200_OK: UserEmailExistsResponseSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        exists = False
        is_active = None
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get('email')
        if self.get_queryset().filter(email=email).count() > 0:
            exists = True
            user = self.get_queryset().filter(email=email).first()
            is_active = user.is_active
        response_serializer = UserEmailExistsResponseSerializer({"exists": exists, "is_active": is_active})
        return Response(response_serializer.data, status.HTTP_200_OK)


class UserConfirmPhoneView(generics.CreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserConfirmPhoneSerializer

    def __init__(self):
        super().__init__()
        self.user_service = UserService()

    @extend_schema(
        request=UserConfirmPhoneSerializer,
        responses={
            status.HTTP_200_OK: StatusResponseSerializer,
            status.HTTP_400_BAD_REQUEST: StatusResponseSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            validated_date = serializer.validated_data
            user = request.user
            self.user_service.generate_and_send_otp_code(user, validated_date.get('phone'))
            return Response({"status": True}, status.HTTP_200_OK)
        except Exception as e:
            return Response({"status": False, "error": e}, status.HTTP_400_BAD_REQUEST)


class UserVerifyPhoneOTPView(generics.CreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserVerifyPhoneOTPSerializer

    def __init__(self):
        super().__init__()
        self.user_service = UserService()

    @extend_schema(
        request=UserVerifyPhoneOTPSerializer,
        responses={
            status.HTTP_200_OK: StatusResponseSerializer,
            status.HTTP_400_BAD_REQUEST: StatusResponseSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            validated_data = serializer.validated_data
            user = request.user
            if not self.user_service.verify_otp_code(user, validated_data.get("otp_code")):
                return Response({"status": False}, status.HTTP_400_BAD_REQUEST)
            return Response({"status": True}, status.HTTP_200_OK)
        except Exception as e:
            return Response({"status": False, "error": e}, status.HTTP_400_BAD_REQUEST)


class UpdateUserPermissionGroupView(generics.UpdateAPIView):
    permission_classes = (IsAuthenticated, UserIsAdmin, UserInSameCompany)
    serializer_class = UpdateUserPermissionGroupSerializer

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_date = serializer.validated_data
        user = User.objects.get(pk=kwargs['id'])
        user = CustomerAPIService().update_user_group(user, validated_date.get('group'))
        return Response(UserSerializer(user).data, status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        self.update(request, *args, **kwargs)

    @extend_schema(
        request=UpdateUserPermissionGroupSerializer,
        responses={
            status.HTTP_200_OK: UserSerializer
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        request=UpdateUserPermissionGroupSerializer,
        responses={
            status.HTTP_200_OK: UserSerializer
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

class RemoveUserCompanyView(generics.UpdateAPIView):
    permission_classes = (IsAuthenticated, UserIsAdmin, UserInSameCompany)
    serializer_class = UserSerializer

    def update(self, request, *args, **kwargs):
        user = User.objects.get(pk=kwargs['id'])
        user.company = None
        user.save()

        return Response(self.get_serializer(user).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=None,
        responses={
            status.HTTP_200_OK: UserSerializer
        }
    )
    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @extend_schema(
        request=None,
        responses={
            status.HTTP_200_OK: UserSerializer
        }
    )
    def patch(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
