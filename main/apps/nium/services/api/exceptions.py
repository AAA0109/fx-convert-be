from rest_framework.exceptions import APIException


class NiumAPIException(APIException):
    ...


class BadRequest(NiumAPIException):
    default_detail = 'The request could not be understood by the server due to malformed syntax'


class Unauthorized(NiumAPIException):
    default_detail = 'The request requires user authentication.'


class Forbidden(NiumAPIException):
    default_detail = 'The server understood the request, but is refusing to fulfill it.'


class NotFound(NiumAPIException):
    default_detail = 'The requested resource could not be found.'


class MethodNotAllowed(NiumAPIException):
    default_detail = ('The method specified in the Request-Line is not allowed for'
                      ' the resource identified by the Request-URI.')


class TooManyRequests(NiumAPIException):
    default_detail = 'Request counts exceed our limit. Slow down!'


class Gone(NiumAPIException):
    default_detail = 'The resource has been gone.'


class InternalServerError(NiumAPIException):
    default_detail = 'Nium had a problem with our server. Try again later.'


class ServiceUnavailable(NiumAPIException):
    default_detail = 'Nium is temporarily offline for maintenance. Please try again later.'
