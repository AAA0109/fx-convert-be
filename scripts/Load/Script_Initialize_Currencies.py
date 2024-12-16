"""
Script that creates all major currencies and loads them into the database.

Added: 12-Mar-2022 NCR
"""

import os
import sys

from hdlib.Core.Currency import all_major_currency
from scripts.lib.only_local import only_allow_local


def run():
    from main.apps.currency.models import Currency

    # Add all the major currencies to the database.
    for name, currency in all_major_currency.items():
        Currency.create_currency_from_hdl(currency)


if __name__ == '__main__':
    # If the connected DB is the remote (real) server, do not allow the program to run.
    only_allow_local()

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django
    django.setup()

    run()
