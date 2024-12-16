import base64
import json

from rest_framework.authentication import TokenAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed


class BearerTokenAuthentication(TokenAuthentication):
    keyword = 'Bearer'

    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = 'Invalid token header. No credentials provided.'
            raise AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = 'Invalid token header. Token string should not contain spaces.'
            raise AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = 'Invalid token header. Token string should not contain invalid characters.'
            raise AuthenticationFailed(msg)

        # Check if the token is a JWT
        if self.is_jwt(token):
            # If it's a JWT, return None to skip this authentication method
            return None

        # If it's not a JWT, proceed with token authentication
        return super().authenticate(request)

    def is_jwt(self, token):
        parts = token.split('.')
        if len(parts) != 3:
            return False

        try:
            # Try to decode the payload (second part of the token)
            payload = parts[1]
            # Add padding if necessary
            payload += '=' * ((4 - len(payload) % 4) % 4)
            decoded = base64.b64decode(payload)
            json.loads(decoded)
            return True
        except (TypeError, ValueError, json.JSONDecodeError):
            return False
