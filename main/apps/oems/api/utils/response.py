from http import HTTPStatus
from typing import List

from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiExample

# =========

from rest_framework import serializers

class ErrorSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    code = serializers.IntegerField()
    data = serializers.JSONField()

# =========

def get_status_description(status_code):
    """Return the standard description for an HTTP status code."""
    try:
        # HTTPStatus uses the status code as an enum to get its name and description
        return HTTPStatus(status_code).phrase
    except ValueError:
        # If the status code is not a valid HTTP status code, handle the error as needed
        return None

class ErrorResponse(Response):
    """
    An API response class for returning error responses with a specific structure.
    """

    def __init__(self, message: str, status: int=status.HTTP_400_BAD_REQUEST, code: int=None, errors: List[str]=None, extra_data=None, **kwargs) -> None:

        assert len(message)

        data = {
            'status': get_status_description(status),
            'message': message,
        }

        if code is not None:
            data['code'] = code

        if errors:
            data['errors'] = errors

        if extra_data:
            data['data'] = extra_data

        # Initialize the parent response with the custom data and status code
        super().__init__(data=data, status=status, **kwargs)

class MultiResponse(Response):

    """
    An API response class for returning error responses with a specific structure.
    """

    def __init__(self, responses: list, status: int=status.HTTP_207_MULTI_STATUS, **kwargs) -> None:

        combined = []

        for response in responses:
            try:
                status = response.status
            except Exception as e:
                status = response.status_code
            combined.append({ 'data': response.data, 'status': status })

        # Initialize the parent response with the custom data and status code
        super().__init__(data=combined, status=status, **kwargs)

# ====================
# docs stuff


INTERNAL_ERROR_RESPONSE = ErrorResponse('internal error', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

IdempotencyParameter = OpenApiParameter(
    name='x-idempotency-key',
    description='Optional idempotency key to handle network disruptions. Max 255 characters. We recommend uuid4.',
    required=False,
    type=str,
    location=OpenApiParameter.HEADER,
)

EXTERNAL_PANGEA_400 = OpenApiResponse(response=ErrorSerializer, description=get_status_description(400),examples=[
                OpenApiExample( name='Example',
                    value={'status': get_status_description(400), 'message': 'error message', 'code': 400}
                )])

EXTERNAL_PANGEA_401 = OpenApiResponse(response=ErrorSerializer, description=get_status_description(401),examples=[
                OpenApiExample( name='Example',
                    value={'status': get_status_description(401), 'message': 'error message', 'code': 401}
                )])


EXTERNAL_PANGEA_403 = OpenApiResponse(response=ErrorSerializer, description=get_status_description(403),examples=[
                OpenApiExample( name='Example',
                    value={'status': get_status_description(403), 'message': 'error message', 'code': 403}
                )])

EXTERNAL_PANGEA_404 = OpenApiResponse(response=ErrorSerializer, description=get_status_description(404),examples=[
                OpenApiExample( name='Example',
                    value={'status': get_status_description(404), 'message': 'validation error', 'code': 404, 'errors':['some error']}
                )])

EXTERNAL_PANGEA_406 = OpenApiResponse(response=ErrorSerializer, description=get_status_description(406),examples=[
                OpenApiExample( name='Example',
                    value={'status': get_status_description(406), 'message': 'invalid action', 'code': 406}
                )])

EXTERNAL_PANGEA_409 = OpenApiResponse(response=ErrorSerializer, description=get_status_description(409),examples=[
                OpenApiExample( name='Example',
                    value={'status': get_status_description(409), 'message': 'resource conflict', 'code': 409}
                )])

EXTERNAL_PANGEA_410 = OpenApiResponse(response=ErrorSerializer, description=get_status_description(410),examples=[
                OpenApiExample( name='Example',
                    value={'status': get_status_description(410), 'message': 'quote expired', 'code': 410}
                )])


EXTERNAL_PANGEA_500 = OpenApiResponse(response=ErrorSerializer, description=get_status_description(500),examples=[
                OpenApiExample( name='Example',
                    value={'status': get_status_description(500), 'message': 'internal error', 'code': 500}
                )])

EXTERNAL_PANGEA_207 = OpenApiResponse(description='array of responses')

