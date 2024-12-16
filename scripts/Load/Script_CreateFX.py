import os
import sys

from hdlib.AppUtils.log_util import get_logger, logging


logger = get_logger(level=logging.INFO)


if __name__ == '__main__':
    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    fxpairs = ["AUDUSD", "EURUSD", "USDCAD", "USDMXN", "USDCNY", "USDCNH", "USDHKD", "USDJPY", "GBPUSD", "USDKRW",
               "USDSGD", "USDILS", "USDBRL", "USDBRR", "USDTHB", "USDTHO", "USDIDR", "USDIDF", "USDINR", "USDINF",
               "USDCHF", "USDCZK", "USDDKK", "USDNOK", "USDHUF", "USDPLN", "USDSEK", "USDZAR", "USDKES", "USDKEF",
               "USDPHP", "USDPHF", "USDTWD", "USDTWF", "NZDUSD", "USDTRF", "USDTRY", "USDSAR", "USDMYR", "USDMYF",
               "USDAED", "USDAEF", "USDKRF"]

    from main.apps.currency.scripts.create_currencies import create_fx_pairs
    
    create_fx_pairs(fxpairs=fxpairs)
