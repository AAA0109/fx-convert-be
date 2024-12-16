"""
Script that deletes company_hedge_actions, company position, order requests, etc.
"""

import os
import sys

from scripts.lib.only_local import only_allow_local


def run():
    from main.apps.hedge.models import FxPosition, AccountHedgeRequest, CompanyHedgeAction, OMSOrderRequest

    FxPosition.objects.all().delete()
    AccountHedgeRequest.objects.all().delete()
    CompanyHedgeAction.objects.all().delete()
    OMSOrderRequest.objects.all().delete()

    print("Deleted FxPosition, AccountHedgeRequest, CompanyHedgeAction, OMSOrderRequest")


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


