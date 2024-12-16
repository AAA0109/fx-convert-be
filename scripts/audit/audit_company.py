# Logging.
from hdlib.AppUtils.log_util import get_logger, logging

logger = get_logger(level=logging.INFO)


def replay_hedge(hedge_id: int):
    from main.apps.auditing.services.auditing import AuditingService

    auditing = AuditingService()
    auditing.replay_hedge(hedge_id)


def audit_company_for_account_id(account_id: int):
    from main.apps.auditing.services.auditing import AuditingService
    from main.apps.account.models import Account

    account = Account.get_account(account_id)
    company = account.company

    auditing = AuditingService()
    auditing.audit_company(company=company, do_corrections=True)


def audit_company_for_company_id(company_id: int):
    from main.apps.auditing.services.auditing import AuditingService
    from main.apps.account.models import Company

    company = Company.get_company(company_id)

    auditing = AuditingService()
    auditing.audit_company(company=company, do_corrections=False, live_positions=True)


if __name__ == '__main__':
    import os, sys

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    replay_hedge(522)

    # audit_company_for_account_id(account_id=5)
    # audit_company_for_company_id(company_id=16)
