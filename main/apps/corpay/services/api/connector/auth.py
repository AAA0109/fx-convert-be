import logging

from main.apps.corpay.services.api.connector.base import CorPayAPIBaseConnector
from main.apps.corpay.services.auth.jwt import CorPayJWTService

logger = logging.getLogger(__name__)


class CorPayAPIAuthConnector(CorPayAPIBaseConnector):
    def __init__(self):
        super().__init__()
        self.jwt = CorPayJWTService()

    def partner_level_token_login(self):
        url = f"{self.api_url}/api/partner/oauth2/token"
        token = self.jwt.get_partner_level_jwt_token()
        data = {
            "assertion": token,
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer"
        }
        response = self.make_request(method='post', url=url, data=data)
        return self.handle_response(response)

    def client_level_token_login(self, user_id: str, client_level_signature: str, partner_access_code: str):
        url = f"{self.api_url}/api/partner/oauth2/userToken"
        token = self.jwt.get_client_level_jwt_token(user_id=user_id, client_level_signature=client_level_signature)
        data = {
            "assertion": token,
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer"
        }
        headers = self.get_headers(access_code=partner_access_code)
        response = self.make_request(method='post', url=url, data=data, headers=headers)
        return self.handle_response(response)
