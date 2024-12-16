from django.db import models
from django.utils.translation import gettext as _


# =============

class BrokerProviderOption(models.TextChoices):
    CORPAY = "CORPAY", _("CORPAY")
    IBKR = "IBKR", _("IBKR")
    CORPAY_MP = 'CORPAY_MP', _("CORPAY_MP")
    VERTO = 'VERTO', _("VERTO")
    NIUM = 'NIUM', _("NIUM")
    AZA = 'AZA', _("AZA")
    MONEX = 'MONEX', _("MONEX")
    CONVERA = 'CONVERA', _("CONVERA")
    OFX = 'OFX', _("OFX")
    XE = 'XE', _("XE")
    OANDA = 'OANDA', _("OANDA")
    AIRWALLEX = 'AIRWALLEX', _("AIRWALLEX")


class BrokerExecutionMethodOptions(models.TextChoices):
    ASYNCHRONOUS = "asynchronous", _("Asynchronous")
    SYNCHRONOUS = "synchronous", _("Synchronous")
    MANUAL = "manual", _("Manual")


class ExecutionTypes(models.TextChoices):
    RFQ = "rfq", "rfq"
    QUOTE_LOCK = "quote_lock", "quote_lock"
    LIMIT = "limit", "limit"
    MARKET = "market", "market"
    TWAP = "twap", "twap"
    VWAP = "vwap", "vwap"
    VOICE = "voice", "voice"
    ALGO = "algo", "algo"


class ApiTypes(models.TextChoices):
    REST = 'rest', 'rest'
    FIX = 'fix', 'fix'
    WEBSOCKET = 'websocket', 'websocket'
    PYTHON_SDK_SYNC = 'python_sdk_sync', 'python_sdk_sync'
    PYTHON_SDK_ASYNC = 'python_sdk_async', 'python_sdk_async'
    MANUAL = 'manual', 'manual'


class FundingModel(models.TextChoices):
    PREFUNDED = 'prefunded', 'prefunded'
    POSTFUNDED = 'postfunded', 'postfunded'
    PREMARGINED = 'premargined', 'premargined'
    POSTMARGINED = 'postmargined', 'postmargined'
    FLEXIBLE = 'flexible', 'flexible'


class FeeType(models.TextChoices):
    BPS = 'bps', 'bps'
    PCT = 'pct', 'pct'
    USD = 'usd', 'usd'
    LOCAL = 'local', 'local'


class RfqTypes(models.TextChoices):
    API = 'api', 'API'
    MANUAL = 'manual', 'MANUAL'
    UNSUPPORTED = 'unsupported', 'UNSUPPORTED'
    INDICATIVE = 'indicative', 'INDICATIVE'
    NORFQ = 'norfq', 'NORFQ'
