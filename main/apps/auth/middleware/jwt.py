from django.contrib.auth.middleware import get_user
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject

from rest_framework_simplejwt.authentication import JWTAuthentication


class JWTAuthenticationMiddleware(MiddlewareMixin):

    def process_request(self, request):
        user = self.__class__.get_jwt_user(request)
        if user is not None:
            request.user = SimpleLazyObject(lambda: user)

    @staticmethod
    def get_jwt_user(request):
        user = get_user(request)
        if user.is_authenticated:
            return user
        jwt_authentication = JWTAuthentication()
        if jwt_authentication.get_header(request):
            result = jwt_authentication.authenticate(request)
            if result is not None:
                user, jwt = result
                return user
        return None
