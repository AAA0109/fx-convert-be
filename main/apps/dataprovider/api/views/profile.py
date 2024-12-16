import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from main.apps.core.auth.permissions import IsInternalSystemUser
from main.apps.dataprovider.api.serializers.profile import ProfileParallelOptionRequestSerializer, \
    ProfileParallelOptionResponseSerializer
from main.apps.dataprovider.models.profile import ProfileParallelOption

logger = logging.getLogger(__name__)


class RetrieveProfileParallelOptionView(APIView):
    permission_classes = [IsInternalSystemUser]

    @extend_schema(
        parameters=[ProfileParallelOptionRequestSerializer],
        responses={
            status.HTTP_200_OK: ProfileParallelOptionResponseSerializer
        }
    )
    def get(self, request, format=None):
        serializer = ProfileParallelOptionRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        profile_id = serializer.validated_data.get('profile_id')
        option = ProfileParallelOption.objects.filter(profile_id=profile_id).first()
        response_serializer = ProfileParallelOptionResponseSerializer(
            {
                "field": option.field if option is not None else None,
                "ids": option.generate_dynamic_ids() if option is not None else []
            }
        )

        return Response(response_serializer.data)



