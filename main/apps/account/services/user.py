import random
from abc import ABC

import math
from rest_framework_simplejwt.tokens import RefreshToken

from main.apps.account.models import User
from main.apps.core import utils
from main.apps.core.models import Config
from main.apps.notification.services.sms_service import SmsService


class UserService(ABC):
    def __init__(self):
        self.sms_service = SmsService()

    def generate_and_send_otp_code(self, user: User, phone: str):
        user.phone = phone
        user.phone_confirmed = False
        user.phone_otp_code = self.generate_otp_code(length=6)
        user.save()
        message = f"""Hello from Pangea Prime, NEVER Share this code via call/text. ONLY YOU should enter the code. BEWARE: IF someone asks for the code, it's a scam. Code: {user.phone_otp_code}"""
        return self.sms_service.send_sms(
            to=user.phone.as_e164,
            body=message
        )

    def verify_otp_code(self, user, otp_code):
        if user.phone_otp_code == otp_code:
            user.phone_confirmed = True
            user.save()
            return True
        return False

    def generate_otp_code(self, length: int = 6):
        digits = "0123456789"
        otp = ""
        for i in range(length):
            otp += digits[math.floor(random.random() * 10)]
        return otp

    @staticmethod
    def generate_token_url(user: User):
        token = RefreshToken.for_user(user)
        fe = Config.get_config('admin/frontend/login_path')
        params = {**{fe.value['token_param']: str(token.access_token)}, **fe.value['extra_query_params']}
        return utils.get_frontend_url(fe.value['path'], **params)
