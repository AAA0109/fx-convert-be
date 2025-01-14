"""
Django settings for main project.

Generated by "django-admin startproject" using Django 3.2.8.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""
import logging
import os
from pathlib import Path

import environ
from corsheaders.defaults import default_headers
from decouple import Csv, config

env = environ.Env(DEBUG=(bool, True))
# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR
FRONTEND_DIR = BASE_DIR.parent / "frontend"

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY", "django-insecure-d&y&au7r&f9b97_$fslnvvd&xzm(*#(2)y5gt104r^eosuz5%_")

# SECURITY WARNING: don"t run with debug turned on in production!
DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv())


GCP_PROJECT_ID = config("GCP_PROJECT_ID", default="GCP_PROJECT_ID", cast=str)

# Application definition
INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "polymorphic",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "post_office",
    "import_export",
    "massadmin",
    "health_check",  # required
    "health_check.db",  # stock Django health checkers
    "health_check.cache",
    "health_check.storage",
    "health_check.contrib.migrations",
    "corsheaders",
    "django_extensions",
    "django_filters",
    "rest_framework",
    "rest_framework.authtoken",
    "django_rest_passwordreset",
    "rest_framework_simplejwt",
    "drf_simple_invite",
    "main.apps.custom_trench.apps.CustomTrenchConfig",
    "django_admin_inline_paginator",
    "drf_spectacular",
    "django_countries",
    "admin_extra_buttons",
    "phonenumber_field",
    "multiselectfield",
    "recurrence",
    "daterangefilter",
    "celery",
    "django_celery_results",
    "django_celery_beat",
    "main.apps.core",
    "main.apps.currency",
    "main.apps.marketdata",
    "main.apps.dataprovider",
    "main.apps.oems",
    "main.apps.broker",
    "main.apps.account",
    "main.apps.cashflow",
    "main.apps.strategy",
    "main.apps.settlement",
    "main.apps.webhook",
    "main.apps.events",
    "main.apps.ibkr",
    "main.apps.corpay",
    "main.apps.nium",
    "main.apps.monex",
    "main.apps.risk_metric",
    "main.apps.hedge",
    "main.apps.history",
    "main.apps.payment",
    "main.apps.billing",
    "main.apps.notification",
    "main.apps.hubspot",
    "main.apps.margin",
    "main.apps.country",
    "main.apps.ndl",
    "main.apps.reports",
    "main.apps.marketing",
    "main.apps.pricing",
    "main.apps.auth_proxy",
    "main.apps.approval",
    "auditlog",
    "gm2m",
]


MIDDLEWARE = [
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_context_request.RequestContextMiddleware",
    "main.apps.auth.middleware.jwt.JWTAuthenticationMiddleware",
    "main.apps.auth.middleware.token.TokenAuthenticationMiddleware",
    "main.apps.auth.middleware.basic.BasicAuthenticationMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
    "idempotency_key.middleware.ExemptIdempotencyKeyBetterLockMiddleware",
]

ROOT_URLCONF = "main.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            FRONTEND_DIR / "build",
            BASE_DIR / "templates"
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "main.wsgi.application"

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT")
    }
}

DATABASE_URL = config("DATABASE_URL", default="", cast=str)
if DATABASE_URL:
    DATABASES = {"default": env.db()}
    # If the flag as been set, configure to use proxy
    if config("USE_CLOUD_SQL_AUTH_PROXY", default="", cast=str):
        DATABASES["default"]["HOST"] = "127.0.0.1"
        DATABASES["default"]["PORT"] = 5432

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = config("LANGUAGE_CODE", default="en-us")

TIME_ZONE = config("TIME_ZONE", default="UTC")

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOCALE_PATHS = [BASE_DIR / "locale"]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = "/static/"

STATIC_ROOT = BACKEND_DIR / "static"

STATICFILES_DIRS = [FRONTEND_DIR / "build" / "static"]

STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

WHITENOISE_ROOT = FRONTEND_DIR / "build" / "root"

# Media files
MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR.parent / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATA_UPLOAD_MAX_NUMBER_FIELDS = config("DATA_UPLOAD_MAX_NUMBER_FIELDS", default=10240)

# ==============================================================================
# Rest Framework SETTINGS
# ==============================================================================
REST_FRAMEWORK = {
    # Use Django"s standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly"
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.TokenAuthentication",
        "main.apps.auth.authentication.BearerTokenAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter"
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning",
}


SPECTACULAR_SETTINGS = {
    "TITLE": "Pangea Prime API",
    "DESCRIPTION": "This is your guide for interacting with the Pangea Prime backend",
    "VERSION": "v1",
    "CONTACT": {"email": "jay@pangea.io"},
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/(v[0-9]+/)?",
    "ENUM_NAME_OVERRIDES": {
        "GroupEnum": "main.apps.account.models.User.UserGroups",
        "SettlementAccountDeliveryMethodEnum": "main.apps.corpay.api.serializers.choices.SETTLEMENT_ACCOUNT_DELIVERY_METHODS",
        "CorpayLockSideEnum": "main.apps.corpay.models.choices.Locksides",
        "RollConventionEnum": "main.apps.account.models.cashflow.BaseCashFlow.RollConvention",
        "FundingRequestStatusEnum": "main.apps.ibkr.models.fb.AbstractFundingRequestResult.Status",
        "StrategyStatusEnum": "main.apps.strategy.models.strategy.HedgingStrategy.Status",
        "InstructDealRequestDeliveryMethodEnum": "main.apps.corpay.api.serializers.choices.DELIVERY_METHODS",
        "DepositRequestMethodEnum": "main.apps.ibkr.api.serializers.fb.DepositRequestSerializer.METHODS",
        "WithdrawRequestMethodEnum": "main.apps.ibkr.api.serializers.fb.WithdrawRequestSerializer.METHODS",
        "PaymentDeliveryMethodEnum": "main.apps.payment.api.serializers.choices.DELIVERY_METHODS"
    },
    "SORT_OPERATIONS": False,
}

# ==============================================================================
# THIRD-PARTY SETTINGS
# ==============================================================================

TRENCH_AUTH = {
    "FROM_EMAIL": "noreply@em3046.pangea.io",
    "APPLICATION_ISSUER_NAME": "PangeaTechnologiesInc",
    "MFA_METHODS": {
        "app": {
            "VERBOSE_NAME": "app",
            "VALIDITY_PERIOD": 30,
            "USES_THIRD_PARTY_CLIENT": True,
            "HANDLER": "trench.backends.application.ApplicationMessageDispatcher",
        },
        "sms_twilio": {
            "VERBOSE_NAME": "sms_twilio",
            "VALIDITY_PERIOD": 30,
            "HANDLER": "trench.backends.twilio.TwilioMessageDispatcher",
            "SOURCE_FIELD": "phone_number",
            "TWILIO_MESSAGING_SERVICE_SID": config("TWILIO_MESSAGING_SERVICE_SID", default=None),
        },
    },
}

# ==============================================================================
# IB SETTINGS
# ==============================================================================

IB_GATEWAY_URL = config("IB_GATEWAY_URL", default="127.0.0.1")
IB_GATEWAY_PORT = config("IB_GATEWAY_PORT", default=7496)
IB_GATEWAY_CLIENT_ID = config("IB_GATEWAY_CLIENT_ID", default=1)
IB_GATEWAY_USE_STATIC_CLIENT_ID = config("IB_GATEWAY_USE_STATIC_CLIENT_ID", default=False, cast=bool)

IB_MD_GATEWAY_URL = config("IB_MD_GATEWAY_URL", default="127.0.0.1")
IB_MD_GATEWAY_PORT = config("IB_MD_GATEWAY_PORT", default=4002)
IB_MD_GATEWAY_CLIENT_ID = config("IB_MD_GATEWAY_CLIENT_ID", default=1)

IB_CLIENT_PORTAL_URL = config("IB_CLIENT_PORTAL_URL", default="127.0.0.1")
IB_CLIENT_PORTAL_PORT = config("IB_CLIENT_PORTAL_PORT", default=5000)

IB_DAM_URL = config("IB_DAM_URL", default="https://qa.interactivebrokers.com")
IB_DAM_CSID = config("IB_DAM_CSID", default="ADA23003105290217B36193E59A4EEEDA3DCACD09A94E56A784C0BD72C6A473A")

IB_RUN_TESTS = config("IB_RUN_TESTS", default=False, cast=bool)
IB_DAM_FB_TEST_BROKER_ACCOUNT_ID = config("IB_DAM_FB_TEST_BROKER_ACCOUNT_ID", default="U1401284")

TWS_CLIENTID_RESERVATION_API_URL = config("TWS_CLIENTID_RESERVATION_API_URL", default="", cast=str)
TWS_CLIENTID_RESERVATION_MAX_RETRIES = config("TWS_CLIENTID_RESERVATION_MAX_RETRIES", default=3, cast=int)
TWS_CLIENTID_RESERVATION_TIMEOUT_SECONDS = config("TWS_CLIENTID_RESERVATION_TIMEOUT_SECONDS", default=10 * 60,
                                                  cast=int)
TWS_CLIENTID_RESERVATION_WAIT_BEFORE_RETRY_SECONDS = config("TWS_CLIENTID_RESERVATION_WAIT_BEFORE_RETRY_SECONDS",
                                                            default=60, cast=int)

GPG_HOME_DIR = config("GPG_HOME_DIR", default="/")
GPG_PASSPHRASE = config("GPG_PASSPHRASE", default="")
GPG_RECIPIENT = config("GPG_RECIPIENT", default="")
GPG_SIGNER = config("GPG_SIGNER", default="")

# ==============================================================================
# OEMS SETTINGS
# ==============================================================================

OEMS_URL = config("OEMS_URL", default="127.0.0.1")
OEMS_PORT = config("OEMS_PORT", default=None)
OEMS_USER = config("OEMS_USER", default=None)
OEMS_PASSWORD = config("OEMS_PASSWORD", default=None)

OEMS_API_URL = config("OEMS_API_URL", default=OEMS_URL)
OEMS_API_PORT = config("OEMS_API_PORT", default=OEMS_PORT)
OEMS_API_USER = config("OEMS_API_USER", default=OEMS_USER)
OEMS_API_PASSWORD = config("OEMS_API_PASSWORD", default=OEMS_PASSWORD)
OEMS_EMAIL_RECIPIENTS = config("OEMS_EMAIL_RECIPIENTS", default="", cast=Csv())
OEMS_NO_TRADING = config("OEMS_NO_TRADING", default=False, cast=bool)

VICTOR_OPS_API_ID = config("VICTOR_OPS_API_ID", default=None)
VICTOR_OPS_API_KEY = config("VICTOR_OPS_API_KEY", default=None)
VICTOR_OPS_ENABLED = config("VICTOR_OPS_ENABLED", default=False, cast=bool)

# ==============================================================================
# CORS SETTINGS
# ==============================================================================

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http(s)?:\/\/(localhost|web|0\.0\.0\.0|127\.0\.0\.1):(8000|8080|3000|3002)",
    r"^http(s)?:\/\/dashboard\.pangea\.io",
    r"^http(s)?:\/\/dashboard\.(.*)\.pangea\.io",
    r"^http(s)?:\/\/prime\.pangea\.io",
    r"^http(s)?:\/\/prime\.(.*)\.pangea\.io",
    r"^http(s)?:\/\/((([\w-]+)?(\d+)?)--)?servant-pangea-web\.netlify\.app",
    r"^http(s)?:\/\/((([\w-]+)?(\d+)?)--)?pangea-prime\.netlify\.app",
    r"^https://pangeaio\.webflow\.io",
    r"^https://www\.pangea\.io",
]

CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-pangea-cv"
]

# ==============================================================================
# API KEYS SETTINGS
# ==============================================================================

# Stripe Settings
STRIPE_API_KEY = config("STRIPE_API_KEY", default=None)

# Hubspot Settings
HUBSPOT_ACCESS_TOKEN = config("HUBSPOT_ACCESS_TOKEN", default=None)
HUBSPOT_TICKET_OWNER_ID = config("HUBSPOT_TICKET_OWNER_ID", default=None)
HUBSPOT_RUN_TESTS = config("HUBSPOT_RUN_TESTS", default=False, cast=bool)

# Twilio Settings
SENDGRID_API_KEY = config("SENDGRID_API_KEY", default=None)
TWILIO_ACCOUNT_SID = config("TWILIO_ACCOUNT_SID", default=None)
TWILIO_AUTH_TOKEN = config("TWILIO_AUTH_TOKEN", default=None)
TWILIO_MESSAGING_SERVICE_SID = config("TWILIO_MESSAGING_SERVICE_SID", default=None)

# Set environment variables for Twilio if they are not None
if TWILIO_ACCOUNT_SID is not None:
    os.environ["TWILIO_ACCOUNT_SID"] = TWILIO_ACCOUNT_SID

if TWILIO_AUTH_TOKEN is not None:
    os.environ["TWILIO_AUTH_TOKEN"] = TWILIO_AUTH_TOKEN

if TWILIO_MESSAGING_SERVICE_SID is not None:
    os.environ["TWILIO_MESSAGING_SERVICE_SID"] = TWILIO_MESSAGING_SERVICE_SID

# ==============================================================================
# CORPAY SETTINGS
# ==============================================================================

CORPAY_PARTNER_LEVEL_USER_ID = config("CORPAY_PARTNER_LEVEL_USER_ID", default=None)
CORPAY_PARTNER_LEVEL_SIGNATURE = config("CORPAY_PARTNER_LEVEL_SIGNATURE", default=None)
CORPAY_CLIENT_LEVEL_CODE = config("CORPAY_CLIENT_LEVEL_CODE", default=None)
CORPAY_CLIENT_LEVEL_USER_CODE = config("CORPAY_CLIENT_LEVEL_USER_CODE", default=None)
CORPAY_CLIENT_LEVEL_SIGNATURE = config("CORPAY_CLIENT_LEVEL_SIGNATURE", default=None)
CORPAY_JWT_AUDIENCE = config("CORPAY_JWT_AUDIENCE", default=None)
CORPAY_API_URL = config("CORPAY_API_URL", default="https://crossborder.corpay.com")
CORPAY_RUN_TESTS = config("CORPAY_RUN_TESTS", default=False, cast=bool)

VERTO_CLIENT_ID = config("VERTO_CLIENT_ID", default="", cast=str)
VERTO_API_KEY = config("VERTO_API_KEY", default="", cast=str)
VERTO_API_BASE = config("VERTO_API_BASE", default="", cast=str)
OER_APP_ID = config("OER_APP_ID", default="", cast=str)
NIUM_CLIENT_ID = config("NIUM_CLIENT_ID", default="", cast=str)
NIUM_CUSTOMER_HASH_ID = config("NIUM_CUSTOMER_HASH_ID", default="", cast=str)
NIUM_API_KEY = config("NIUM_API_KEY", default="", cast=str)
NIUM_API_BASE = config("NIUM_API_BASE", default="", cast=str)
MONEX_CLIENT_ID = config("MONEX_CLIENT_ID", default="", cast=str)
MONEX_API_KEY = config("MONEX_API_KEY", default="", cast=str)
MONEX_API_BASE = config("MONEX_API_BASE", default="", cast=str)
MONEX_DEV_USERNAME = config("MONEX_DEV_USERNAME", default="", cast=str)
MONEX_DEV_PASSWORD = config("MONEX_DEV_PASSWORD", default="", cast=str)
MONEX_ENTITY_ID = config("MONEX_ENTITY_ID", default="", cast=str)
MONEX_CUSTOMER_ID = config("MONEX_CUSTOMER_ID", default="", cast=str)
MONEX_COMPANY_NAME = config("MONEX_COMPANY_NAME", default="", cast=str)

NSADAQ_DATA_LINK_API_KEY = config("NSADAQ_DATA_LINK_API_KEY", "NSADAQ_DATA_LINK_API_KEY")

# ==============================================================================
# FIRST-PARTY SETTINGS
# ==============================================================================
APP_ENVIRONMENT = config("APP_ENVIRONMENT", default="dev")
API_SCOPE = config("API_SCOPE", default="internal")
OEMS_TRACING = config("OEMS_TRACING", default=(APP_ENVIRONMENT=='production'), cast=bool)

AUTH_USER_MODEL = "account.User"
DEFAULT_FROM_EMAIL = "noreply@em3046.pangea.io"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,  # ADDED
    "formatters": {
        "simple": {
            "format": "[{levelname} | {asctime}]:  {message}",
            "style": "{",
        },
        "verbose": {
            "format": "[{levelname} | {asctime} {module} ({process:d} / {thread:d})]:  {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple"
        }
    },
    "root": {
        "handlers": ["console"],
        "level": config("LOG_LEVEL", "INFO"),
    }
}

# ==============================================================================
# PUB/SUB SETTINGS
# ==============================================================================

pubsub = {
    "GC_CREDENTIALS_PATH": config("GC_CREDENTIALS", default="", cast=str),
    "GC_PROJECT_ID": GCP_PROJECT_ID,
    "ENCODER_PATH": "rest_framework.utils.encoders.JSONEncoder",
    "TOPIC_ID": config("TOPIC_ID", default="", cast=str)
}

# ==============================================================================
# EMAIL SETTINGS
# ==============================================================================

EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = "smtp.sendgrid.net"
EMAIL_HOST_USER = "apikey"  # this is exactly the value "apikey"
EMAIL_HOST_PASSWORD = SENDGRID_API_KEY
EMAIL_PORT = 587
EMAIL_USE_TLS = True

FRONTEND_URL = config("FRONTEND_URL", "http://127.0.0.1:3000")

POST_OFFICE = {
    "TEMPLATE_ENGINE": "post_office",
}

CASHFLOW_API_CONFIG = {
    "BYPASS_MARGIN_CHECK": False,
}

# ==============================================================================
# SLACK SETTINGS
# ==============================================================================

SLACK_NOTIFICATIONS_APP_BOT_TOKEN = config("SLACK_NOTIFICATIONS_APP_BOT_TOKEN",
                                           default="SLACK_NOTIFICATIONS_APP_BOT_TOKEN")
SLACK_NOTIFICATIONS_CHANNEL = config("SLACK_NOTIFICATIONS_CHANNEL", default="SLACK_NOTIFICATIONS_CHANNEL")
SLACK_RUN_TESTS = config("SLACK_RUN_TESTS", default=False, cast=bool)
SLACK_SIGNING_SECRET = config("SLACK_SIGNING_SECRET", default="", cast=str)

# ==============================================================================
# CLOUD COMPOSER / AIRFLOW SETTINGS
# ==============================================================================
try:
    import google.auth

    AF_PROJECT_ID = GCP_PROJECT_ID
    AF_CLIENT_ID = config("AF_CLIENT_ID", "default-client-id", cast=str)
    AF_ENABLED = config("AF_ENABLED", default=False, cast=bool)
    AF_LOCATION = config("AF_LOCATION", "default-location", cast=str)
    AF_COMPOSER_ENV_NAME = config("AF_COMPOSER_ENV_NAME", "default-composer-env-name", cast=str)
    AF_WEBSERVER_URL = config("AF_WEBSERVER_URL", "https://AF-WEBSERVER.URL", cast=str)
    AF_IAM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
    AF_CREDENTIALS, _ = google.auth.default(scopes=[AF_IAM_SCOPE])
    AF_USE_EXPERIMENTAL_API = False
except Exception as e:
    # logging.exception("Airflow client could not be setup.")
    pass

DASHBOARD_API_URL = config("DASHBOARD_API_URL", default="", cast=str)
DASHBOARD_API_USER = config("DASHBOARD_API_USER", default="", cast=str)
DASHBOARD_API_TOKEN = config("DASHBOARD_API_TOKEN", default="", cast=str)

# ==============================================================================
# REDIS CONFIGURATION OPTIONS
# ==============================================================================
REDIS_HOST = config("REDIS_HOST", default="127.0.0.1")
REDIS_PORT = config("REDIS_PORT", default="6379")
REDIS_URL = config("REDIS_URL", default=f"redis://{REDIS_HOST}:{REDIS_PORT}")

# ==============================================================================
# REDIS WORKER CONFIGURATION OPTIONS
# ==============================================================================
REDIS_WORKER_HOST = config("REDIS_HOST", default="127.0.0.1")
REDIS_WORKER_PORT = config("REDIS_WORKER_PORT", default="6380")
REDIS_WORKER_URL = config("REDIS_URL", default=f"redis://{REDIS_WORKER_HOST}:{REDIS_WORKER_PORT}")

# ==============================================================================
# CELERY CONFIGURATION OPTIONS
# ==============================================================================
try:
    CELERY_TIMEZONE = TIME_ZONE
    CELERY_BROKER_URL = f"{REDIS_URL}/1"
    CELERY_WORKER_URL = f"{REDIS_WORKER_URL}/1"
    CELERYBEAT_SCHEDULER = CELERY_BEAT_SCHEDULER = config("CELERY_BEAT_SCHEDULER",
                                                          default="django_celery_beat.schedulers:DatabaseScheduler")
    CELERY_RESULT_BACKEND = "django-db"
    CELERY_CACHE_BACKEND = "django-cache"
    CELERY_RESULT_EXTENDED = True
    CELERY_REDIS_DB = CELERY_DEFAULT_QUEUE = f"celery_pangea_{APP_ENVIRONMENT}_queue"
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
except Exception as e:
    logging.exception("Error: Celery configurations failed")

# ==============================================================================
# FLOWER CONFIGURATION OPTIONS
# ==============================================================================
FLOWER_UNAUTHENTICATED_API=config("FLOWER_UNAUTHENTICATED_API", default=True, cast=bool)

# ==============================================================================
# DJANGO-IDEMPOTENCY-KEY
# ==============================================================================

from idempotency_key import status

IDEMPOTENCY_KEY = {
    # Specify the key encoder class to be used for idempotency keys.
    # If not specified then defaults to "idempotency_key.encoders.BasicKeyEncoder"
    "ENCODER_CLASS": "idempotency_key.encoders.MaxLengthKeyEncoder",

    # Set the response code on a conflict.
    # If not specified this defaults to HTTP_409_CONFLICT
    # If set to None then the original request"s status code is used.
    "CONFLICT_STATUS_CODE": status.HTTP_409_CONFLICT,

    # Allows the idempotency key header sent from the client to be changed
    "HEADER": "x-idempotency-key",

    # Add telemetry headers
    "TELEMETRY": True,

    "STORAGE": {
        # Specify the storage class to be used for idempotency keys
        # If not specified then defaults to "idempotency_key.storage.MemoryKeyStorage"
        "CLASS": "idempotency_key.storage.CacheKeyStorage",

        # Name of the django cache configuration to use for the CacheStorageKey storage
        # class.
        # This can be overriden using the @idempotency_key(cache_name="MyCacheName")
        # view/viewset function decorator.
        "CACHE_NAME": "default",

        # When the response is to be stored you have the option of deciding when this
        # happens based on the responses status code. If the response status code
        # matches one of the statuses below then it will be stored.
        # The statuses below are the defaults used if this setting is not specified.
        "STORE_ON_STATUSES": [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_202_ACCEPTED,
            status.HTTP_203_NON_AUTHORITATIVE_INFORMATION,
            status.HTTP_204_NO_CONTENT,
            status.HTTP_205_RESET_CONTENT,
            status.HTTP_206_PARTIAL_CONTENT,
            status.HTTP_207_MULTI_STATUS,
        ]
    },

    # The following settings deal with the process/thread lock that can be placed around the cache storage object
    # to ensure that multiple threads do not try to call the same view/viewset method at the same time.
    "LOCK": {
        # Specify the key object locking class to be used for locking access to the cache storage object.
        # If not specified then defaults to "idempotency_key.locks.basic.ThreadLock"
        "CLASS": "idempotency_key.locks.redis.MultiProcessRedisKeyLock",

        # Location of the Redis server if MultiProcessRedisLock is used otherwise this is ignored.
        # The host name can be specified or both the host name and the port separated by a colon ":"
        "LOCATION": REDIS_URL,

        # The unique name to be used accross processes for the lock. Only used by the MultiProcessRedisLock class
        "NAME": "OemsPostLock",

        # The maximum time to live for the lock. If a lock is given and is never released this timeout forces the release
        # The lock time is in seconds and the default is None which means lock until it is manually released
        "TTL": 60.0,

        # The maximum time for a key to live as an integer seconds. Only used by the MultiProcessRedisLock classes
        "KEY_TTL": 86400,

        # The use of a lock around the storage object so that only one thread at a time can access it.
        # By default this is set to true. WARNING: setting this to false may allow duplicate calls to occur if the timing
        # is right.
        "ENABLE": True,

        # If the ENABLE_LOCK setting is True above then this represents the timeout (in seconds as a floating point number)
        # to occur before the thread gives up waiting. If a timeout occurs the middleware will return a HTTP_423_LOCKED
        # response.
        "TIMEOUT": 0.1,
    },

}

# ==============================================================================
# CHANNELS
# ==============================================================================

ASGI_APPLICATION = "main.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
        },
    },
}

# ==============================================================================
# TEST SETTINGS
# ==============================================================================

AI_RUN_TESTS = config("AI_RUN_TESTS", default=False, cast=bool)
AF_RUN_TESTS = config("AF_RUN_TESTS", default=False, cast=bool)
SE_RUN_TESTS = config("SE_RUN_TESTS", default=False, cast=bool)
OEMS_RUN_TESTS = config("OEMS_RUN_TESTS", default=False, cast=bool)

# ==============================================================================
# SILK SETTINGS
# ==============================================================================


SILKY_PYTHON_PROFILER = config("SILKY_PYTHON_PROFILER", default=False, cast=bool)
SILKY_PYTHON_PROFILER_BINARY = config("SILKY_PYTHON_PROFILER_BINARY", default=False, cast=bool)
SILKY_AUTHENTICATION = config("SILKY_AUTHENTICATION", default=True, cast=bool)
def should_profile(request):
    return SILKY_PYTHON_PROFILER
SILKY_INTERCEPT_FUNC = should_profile
if APP_ENVIRONMENT == 'local':
    INSTALLED_APPS.append("silk")
    MIDDLEWARE.append("silk.middleware.SilkyMiddleware")


CORPAY_PANGEA_COMPANY_ID = config("CORPAY_PANGEA_COMPANY_ID", default=None)
