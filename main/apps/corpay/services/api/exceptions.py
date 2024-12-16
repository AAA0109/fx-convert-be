from rest_framework.exceptions import APIException


class CorPayAPIException(APIException):
    ...


class BadRequest(CorPayAPIException):
    ...


class NotFound(CorPayAPIException):
    ...


class Forbidden(CorPayAPIException):
    ...


class Gone(CorPayAPIException):
    ...


class InternalServerError(CorPayAPIException):
    ...
