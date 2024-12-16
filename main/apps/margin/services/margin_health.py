import logging

from hdlib.DateTime.Date import Date

from main.apps.account.models import Company
from main.apps.broker.models import BrokerAccount
from main.apps.ibkr.models import WireInstruction
from main.apps.margin.models.daily_margin_health import DailyMarginDetail
from main.apps.margin.services.margin_service import DefaultMarginProviderService, MarginProviderService
from main.apps.notification.utils.email import send_deposit_required_email, send_low_margin_email

logger = logging.getLogger(__name__)


class MarginHealthService(object):

    def __init__(self, company_id: int, deposit_required_level: float):
        self.company_id = company_id
        self.deposit_required_level = deposit_required_level

    def execute(self):
        try:
            company = Company.get_company(self.company_id)
            if company is None:
                logger.debug(f"Cannot find company with id: {self.company_id}")
                return
            if not BrokerAccount.has_ibkr_broker_account(company):
                logger.error(f"Unable to get IBKR account for company: {company.name}")
                return

            logger.debug(f"Checking margin health for company={self.company_id}.")

            margin_provider_service: MarginProviderService = DefaultMarginProviderService()

            report = margin_provider_service.get_margin_health_report(company=company, custom_amount=None)
            if report is None:
                logger.debug(f"Company {self.company_id} has no margin health report.")
                return
            worst_projected_margin = report.worst_projected_margin()
            worst_health_score = 1.0 if worst_projected_margin is None else worst_projected_margin.health_score()
            best_projected_margin = report.best_projected_margin()
            best_health_score = 1.0 if best_projected_margin is None else best_projected_margin.health_score()
            logger.debug(
                f"Company {self.company_id} has worst margin health score of {worst_health_score} and best margin health score of {best_health_score}.")
            DailyMarginDetail.insert_company_margin_health(company=company,
                                                           worst_margin_health=worst_health_score,
                                                           best_margin_health=best_health_score)
            if worst_health_score >= self.deposit_required_level:
                logger.debug(f"Company {self.company_id} has margin health above {self.deposit_required_level}.")
                return
            yesterday_margin_details = DailyMarginDetail.get_company_margin_healths(company=company,
                                                                                    start_date=Date.today() - 1,
                                                                                    end_date=Date.today())
            if not yesterday_margin_details:
                logger.debug(
                    f"Company {self.company_id} has no margin health details for yesterday this is the first time we run this.")
                deposit_required = False
            else:
                detail = yesterday_margin_details.first()
                if detail.worst_margin_health < self.deposit_required_level:
                    deposit_required = True
                else:
                    deposit_required = False

            logger.debug(
                f"Company {self.company_id} has margin health below {self.deposit_required_level} for the last 30 days.")

            if deposit_required:
                send_deposit_required_email(broker_account=company.broker_accounts.first(),
                                            margin=report.margin_detail,
                                            forcast_margin=worst_projected_margin,
                                            wire_instruction=WireInstruction.objects.first())
            else:
                send_low_margin_email(broker_account=company.broker_accounts.first(),
                                      margin=report.margin_detail,
                                      forcast_margin=worst_projected_margin,
                                      wire_instruction=WireInstruction.objects.first())




        except Exception as e:
            logging.error(e)
            raise Exception(e)
