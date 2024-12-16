from drf_spectacular.utils import extend_schema

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_204_NO_CONTENT

from trench.exceptions import MFAValidationError
from trench.responses import ErrorResponse
from trench.serializers import MFAMethodDeactivationValidator

from trench.views import (
    MFAConfigView,
    MFAListActiveUserMethodsView,
    MFAMethodActivationView,
    MFAMethodBackupCodesRegenerationView,
    MFAMethodConfirmActivationView,
    MFAMethodDeactivationView,
    MFAMethodRequestCodeView,
    MFAPrimaryMethodChangeView
)

from main.apps.auth.api.serializers.trench.base import (
    MFAMethodDetailsResponseSerializer,
    MFAMethodActivationErrorResponseSerializer, MFAConfigViewSuccessResponseSerializer, MFAActiveUserMethodSerializer,
    MFAMethodBackupCodeSuccessResponseSerializer,
    MFAMethodCodeErrorResponseSerializer,
    MFAMethodCodeRequestSerializer, MFAMethodRequestCodeRequestSerializer,
    MFAMethodPrimaryMethodChangeRequestSerializer
)
from main.apps.auth.command.deactivate_mfa_method import deactivate_mfa_method_command


@extend_schema(
    responses={
        status.HTTP_200_OK: MFAConfigViewSuccessResponseSerializer
    }
)
class ExtendMFAConfigView(MFAConfigView):
    pass


@extend_schema(
    responses={
        status.HTTP_200_OK: MFAActiveUserMethodSerializer(many=True)
    }
)
class ExtendMFAListActiveUserMethodsView(MFAListActiveUserMethodsView):
    pagination_class = None
    pass


@extend_schema(
    responses={
        status.HTTP_200_OK: MFAMethodDetailsResponseSerializer,
        status.HTTP_400_BAD_REQUEST: MFAMethodActivationErrorResponseSerializer
    }
)
class ExtendMFAMethodActivationView(MFAMethodActivationView):
    pass


@extend_schema(
    request=MFAMethodCodeRequestSerializer,
    responses={
        status.HTTP_200_OK: MFAMethodBackupCodeSuccessResponseSerializer,
        status.HTTP_400_BAD_REQUEST: MFAMethodCodeErrorResponseSerializer
    }
)
class ExtendMFAMethodBackupCodesRegenerationView(MFAMethodBackupCodesRegenerationView):
    pass


@extend_schema(
    request=MFAMethodCodeRequestSerializer,
    responses={
        status.HTTP_200_OK: MFAMethodBackupCodeSuccessResponseSerializer,
        status.HTTP_400_BAD_REQUEST: MFAMethodCodeErrorResponseSerializer,
    }
)
class ExtendMFAMethodConfirmActivationView(MFAMethodConfirmActivationView):
    pass


@extend_schema(
    request=MFAMethodCodeRequestSerializer,
    responses={
        status.HTTP_204_NO_CONTENT: None,
        status.HTTP_400_BAD_REQUEST: MFAMethodCodeErrorResponseSerializer
    }
)
class ExtendMFAMethodDeactivationView(MFAMethodDeactivationView):
    @staticmethod
    def post(request: Request, method: str) -> Response:
        serializer = MFAMethodDeactivationValidator(
            mfa_method_name=method, user=request.user, data=request.data
        )
        if not serializer.is_valid():
            return Response(status=HTTP_400_BAD_REQUEST, data=serializer.errors)
        try:
            deactivate_mfa_method_command(
                mfa_method_name=method, user_id=request.user.id
            )
            return Response(status=HTTP_204_NO_CONTENT)
        except MFAValidationError as cause:
            return ErrorResponse(error=cause)


@extend_schema(
    request=MFAMethodRequestCodeRequestSerializer,
    responses={
        status.HTTP_204_NO_CONTENT: None,
        status.HTTP_400_BAD_REQUEST: MFAMethodDetailsResponseSerializer
    }
)
class ExtendMFAMethodRequestCodeView(MFAMethodRequestCodeView):
    pass


@extend_schema(
    request=MFAMethodPrimaryMethodChangeRequestSerializer,
    responses={
        status.HTTP_204_NO_CONTENT: None,
        status.HTTP_400_BAD_REQUEST: MFAMethodCodeErrorResponseSerializer
    }
)
class ExtendMFAPrimaryMethodChangeView(MFAPrimaryMethodChangeView):
    pass
