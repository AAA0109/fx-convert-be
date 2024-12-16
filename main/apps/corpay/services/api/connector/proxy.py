import uuid

from main.apps.corpay.services.api.connector.base import CorPayAPIBaseConnector


class CorPayAPIProxyConnector(CorPayAPIBaseConnector):

    def proxy_request(self, url: str, method: str, access_code: str):
        headers = self.get_headers(access_code=access_code)
        response = self.make_request(url=url, method=method, headers=headers)
        return self.handle_response(response)
