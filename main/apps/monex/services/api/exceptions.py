from rest_framework.exceptions import APIException


class MonexAPIException(APIException):
    ...


class BadRequest(MonexAPIException):
    default_detail = 'The request could not be understood by the server due to malformed syntax'


class Unauthorized(MonexAPIException):
    default_detail = 'The request requires user authentication.'


class Forbidden(MonexAPIException):
    default_detail = 'The server understood the request, but is refusing to fulfill it.'


class NotFound(MonexAPIException):
    default_detail = 'The requested resource could not be found.'


class MethodNotAllowed(MonexAPIException):
    default_detail = ('The method specified in the Request-Line is not allowed for'
                      ' the resource identified by the Request-URI.')


class TooManyRequests(MonexAPIException):
    default_detail = 'Request counts exceed our limit. Slow down!'


class Gone(MonexAPIException):
    default_detail = 'The resource has been gone.'


class InternalServerError(MonexAPIException):
    default_detail = 'Monex had a problem with our server. Try again later.'


class ServiceUnavailable(MonexAPIException):
    default_detail = 'Monex is temporarily offline for maintenance. Please try again later.'

