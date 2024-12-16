from rest_framework import serializers
from django.core.exceptions import ValidationError


class OnboardingFileField(serializers.FileField):
    ALLOWED_CONTENT_TYPES = ['application/pdf', 'image/png', 'image/jpeg']

    def to_internal_value(self, data):
        file = super().to_internal_value()
        self.validate_content_type(file)
        return file

    def validate_content_type(self, file):
        if file.content_type not in self.ALLOWED_CONTENT_TYPES:
            raise ValidationError('Invalid file type. Allowed types are PDF, PNG, and JPEG.')
