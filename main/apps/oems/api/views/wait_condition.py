from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status, permissions
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.oems.api.serializers.wait_condition import WaitConditionSerializer
from main.apps.oems.models.wait_condition import WaitCondition


class WaitConditionViewSet(ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasCompanyAssociated]
    queryset = WaitCondition.objects.all()
    serializer_class = WaitConditionSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    def get_queryset(self):
        return WaitCondition.objects.filter(quote__user=self.request.user)

    @extend_schema(
        request=WaitConditionSerializer,
        responses={
            status.HTTP_201_CREATED: WaitConditionSerializer,
        }
    )
    def create(self, request):
        """
        Create wait condition record
        """
        serializer = WaitConditionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wait_condition = WaitCondition(**serializer.validated_data)
        wait_condition.save()

        serializer = WaitConditionSerializer(wait_condition)
        data = serializer.data
        return Response(data, status.HTTP_201_CREATED)

    @extend_schema(
        responses={
            status.HTTP_200_OK: WaitConditionSerializer,
        }
    )
    def retrieve(self, request, id: int):
        """
        Get wait condition record by id
        """
        wait_condition = get_object_or_404(self.get_queryset(), pk=int(id))
        serializer = WaitConditionSerializer(wait_condition)
        return Response(serializer.data)

    @extend_schema(
        request=WaitConditionSerializer,
        responses={
            status.HTTP_200_OK: WaitConditionSerializer,
        }
    )
    def update(self, request, id: int):
        """
        Update wait condition record
        """

        serializer = WaitConditionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wait_condition = WaitCondition.objects.get(id=id)
        for key, value in serializer.validated_data.items():
            setattr(wait_condition, key, value)
        wait_condition.save()

        response = WaitConditionSerializer(wait_condition)

        return Response(response.data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={
            status.HTTP_204_NO_CONTENT: None,
        }
    )
    def destroy(self, request, id: int):
        """
        Remove wait condition record
        """
        WaitCondition.objects.filter(pk=id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
