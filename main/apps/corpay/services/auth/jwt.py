import abc
from typing import Final

from django.conf import settings
from datetime import datetime, timezone, timedelta

import jwt


class CorPayJWTService(abc.ABC):
    AUDIENCE: Final = "cambridgefx"

    def __init__(self):
        self.issuer = settings.CORPAY_PARTNER_LEVEL_USER_ID
        self.partner_level_signature = settings.CORPAY_PARTNER_LEVEL_SIGNATURE

    def get_partner_level_jwt_token(self):
        now = datetime.now(tz=timezone.utc)
        exp = now + timedelta(minutes=20)
        claim = {
            "iss": self.issuer,
            "iat": now,
            "exp": exp,
            "aud": self.AUDIENCE
        }
        encoded = jwt.encode(claim, self.partner_level_signature, algorithm="HS256")
        return encoded

    def get_client_level_jwt_token(self, user_id: str, client_level_signature: str):
        now = datetime.now(tz=timezone.utc)
        exp = now + timedelta(minutes=20)
        claim = {
            "iss": user_id,
            "iat": now,
            "exp": exp,
            "aud": self.AUDIENCE
        }
        encoded = jwt.encode(claim, client_level_signature, algorithm="HS256")
        return encoded

