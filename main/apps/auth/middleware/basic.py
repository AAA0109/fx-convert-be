from django.contrib.auth.middleware import get_user
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject
from rest_framework.authentication import BasicAuthentication


class BasicAuthenticationMiddleware(MiddlewareMixin):

    def process_request(self, request):
        user = self.__class__.get_token_auth_user(request)
        if user is not None:
            request.user = SimpleLazyObject(lambda: user)

    @staticmethod
    def get_token_auth_user(request):
        user = get_user(request)
        if user.is_authenticated:
            return user
        basic_authentication = BasicAuthentication()
        result = basic_authentication.authenticate(request)
        if result:
            user, token = result
            return user
        return None