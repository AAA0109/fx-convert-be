from rest_framework import serializers
from drf_spectacular.extensions import OpenApiSerializerExtension
from drf_spectacular.utils import inline_serializer

class TokenObtainPairSerializerExtension(OpenApiSerializerExtension):
    target_class = 'rest_framework_simplejwt.serializers.TokenObtainPairSerializer'
    priority = 1

    def map_serializer(self, auto_schema, direction):
        Fixed = inline_serializer('Fixed', fields={
            self.target_class.username_field: serializers.CharField(write_only=True),
            'password': serializers.CharField(write_only=True)
        })
        return auto_schema._map_serializer(Fixed, direction)
