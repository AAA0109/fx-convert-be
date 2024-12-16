from drf_spectacular.utils import extend_schema, PolymorphicProxySerializer
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from trench.views.jwt import MFAFirstStepJWTView, MFASecondStepJWTView

from main.apps.auth.api.serializers.trench.base import MFAMethodDetailsResponseSerializer
from main.apps.auth.api.serializers.trench.jwt import MFAFirstStepJWTRequestSerializer, \
    MFAFirstStepJWTMFAEnabledSuccessResponseSerializer, MFAJWTAccessRefreshResponseSerializer, \
    MFASecondStepJWTRequestSerializer


class ExtendMFAFirstStepJWTView(MFAFirstStepJWTView):
    @extend_schema(
        request=MFAFirstStepJWTRequestSerializer,
        responses={
            status.HTTP_200_OK: PolymorphicProxySerializer(
                component_name='MFAFirstStepJWTSuccess',
                serializers=[
                    MFAFirstStepJWTMFAEnabledSuccessResponseSerializer,
                    MFAJWTAccessRefreshResponseSerializer
                ],
                resource_type_field_name=None
            ),
            status.HTTP_401_UNAUTHORIZED: MFAMethodDetailsResponseSerializer
        }
    )
    def post(self, request: Request) -> Response:
        return super().post(request)


class ExtendMFASecondStepJWTView(MFASecondStepJWTView):
    @extend_schema(
        request=MFASecondStepJWTRequestSerializer,
        responses={
            status.HTTP_200_OK: MFAJWTAccessRefreshResponseSerializer,
            status.HTTP_401_UNAUTHORIZED: MFAMethodDetailsResponseSerializer
        }
    )
    def post(self, request: Request) -> Response:
        return super().post(request)
