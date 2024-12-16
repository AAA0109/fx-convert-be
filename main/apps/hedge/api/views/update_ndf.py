import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets, mixins
from rest_framework.permissions import IsAuthenticated

from main.apps.core.utils.api import *
from main.apps.hedge.api.serializers.update_ndf import UpdateNDFSerializer

logger = logging.getLogger(__name__)


class UpdateNDFViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    serializer_class = UpdateNDFSerializer
    http_method_names = ['post']

    @extend_schema(
        request=UpdateNDFSerializer,
        responses={
            status.HTTP_201_CREATED: UpdateNDFSerializer
        }
    )
    def create(self, request, *args, **kwargs) -> Response:
        data = request.data
        data['user'] = request.user.pk
        serializer = self.serializer_class(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_201_CREATED, data=serializer.data)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors)
