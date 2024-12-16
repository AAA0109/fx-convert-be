# flake8: noqa

from google.cloud import logging as gcp_logging

from .base import *

# import sentry_sdk
# from sentry_sdk.integrations.django import DjangoIntegration

# ==============================================================================
# EMAIL SETTINGS
# ==============================================================================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# ==============================================================================
# SECURITY SETTINGS
# ==============================================================================

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7 * 52  # one year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_SSL_REDIRECT = True
if APP_ENVIRONMENT == 'local':
    SECURE_SSL_REDIRECT = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = True

# ==============================================================================
# THIRD-PARTY APPS SETTINGS
# ==============================================================================

# sentry_sdk.init(
#     dsn=config("SENTRY_DSN", default=""),
#     environment=APP_ENVIRONMENT,
#     release="main@%s" % main.__version__,
#     integrations=[DjangoIntegration()],
# )

# ==============================================================================
# GOOGLE STORAGE SETTINGS
# ==============================================================================

# Define static storage via django-storages[google]
GS_BUCKET_NAME = config("GS_BUCKET_NAME", default=None)
GS_LOCATION = config("GS_LOCATION", default="dashboard/")
GS_DATA_PATH = config("GS_DATA_PATH", default="storage/")
GS_DEFAULT_ACL = config("GS_DEFAULT_ACL", "publicRead")
DEFAULT_FILE_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"
STATICFILES_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"

try:
    logging.info("Setting up GCP logging")
    client = gcp_logging.Client()
    client.setup_logging()
    LOGGING["handlers"]["google_cloud_logging"] = {
        "level": config("LOG_LEVEL", default="WARNING"),
        "class": "google.cloud.logging.handlers.CloudLoggingHandler",
        "client": client
    }
    LOGGING["root"]["handlers"].append("google_cloud_logging")
except Exception as e:
    logging.exception("Google Cloud Logging handler could not be setup.")

try:
    # TODO: Use django native redis cache
    # https://docs.djangoproject.com/en/4.1/topics/cache/#redis
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"{REDIS_URL}/1",
            "KEY_PREFIX": APP_ENVIRONMENT,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            }
        }
    }
except Exception as e:
    logging.exception("Cloud Memorystore (Redis) could not be setup.")
