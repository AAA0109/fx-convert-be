from typing import Iterable, Tuple

from main.apps.corpay.services.api.connector.base import CorPayAPIBaseConnector
from main.apps.corpay.services.api.dataclasses.onboarding import OnboardingRequestBody, OnboardingPickListParams, \
    OnboardingAuthSecretKeyParams


class CorPayAPIOnboardingConnector(CorPayAPIBaseConnector):
    def client_onboarding(self, access_code: str, data: OnboardingRequestBody):
        url = f"{self.api_url}/api/clientonboarding"
        response = self.post_request(url=url, access_code=access_code, data=data)
        return response['content']

    def client_onboarding_files(self, access_code: str, client_onboarding_id: str, files=Iterable[Tuple]):
        url = f"{self.api_url}/api/clientonboarding-files/{client_onboarding_id}"
        response = self.post_request(url=url, access_code=access_code, files=files)
        return response['content']

    def onboarding_picklist(self, access_code: str, data: OnboardingPickListParams):
        url = f"{self.api_url}/api/clientonboarding/onboardingpicklists"
        response = self.get_request(url=url, access_code=access_code, data=data)
        return response['content']

    def authsecret_key(self, access_code: str, data: OnboardingAuthSecretKeyParams):
        url = f"{self.api_url}/api/clientonboarding/authsecret"
        response = self.get_request(url=url, access_code=access_code, data=data)
        return response['content']
