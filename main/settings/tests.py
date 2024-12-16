# flake8: noqa

from .base import *

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()
STRIPE_API_KEY = config("TEST_STRIPE_API_KEY", default=None)

CASHFLOW_API_CONFIG = {
    "BYPASS_MARGIN_CHECK": True,
}
AF_ENABLED = config("AF_ENABLED", default=False, cast=bool)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

GS_BUCKET_NAME = config("GS_BUCKET_NAME", default="TEST_GS_BUCKET_NAME")
