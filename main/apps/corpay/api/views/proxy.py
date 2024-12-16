from drf_spectacular.utils import extend_schema, PolymorphicProxySerializer
from rest_framework import status, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from main.apps.corpay.api.serializers.proxy import ProxyRequestSerializer, ProxyCurrencyResponseSerializer, \
    ProxyRegionResponseSerializer, ProxyCountryResponseSerializer
from main.apps.corpay.api.views.base import CorPayBaseView


class CorPayProxyView(CorPayBaseView):

    @extend_schema(
        request=ProxyRequestSerializer,
        responses={
            status.HTTP_200_OK: PolymorphicProxySerializer(
                component_name="proxy",
                serializers=[
                    ProxyCountryResponseSerializer,
                    ProxyCurrencyResponseSerializer,
                    ProxyRegionResponseSerializer,
                ],
                resource_type_field_name=None,
                many=False
            )
        }
    )
    def post(self, request):
        self.corpay_service.init_company(request.user.company)
        serializer = ProxyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        url = serializer.validated_data.get('uri')
        response = self.corpay_service.proxy_request(url=url, method=serializer.validated_data.get('method'))

        last_part = self.corpay_service.get_proxy_url_path(url)
        serializer_map = {
            'regions': ProxyRegionResponseSerializer,
            'countries': ProxyCountryResponseSerializer,
            'payCurrencies': ProxyCurrencyResponseSerializer
        }

        response_serializer = serializer_map.get(last_part, None)
        if response_serializer:
            response_serializer = response_serializer(response)
            return Response(response_serializer.data, status.HTTP_200_OK)
        else:
            return Response(response, status.HTTP_200_OK)
