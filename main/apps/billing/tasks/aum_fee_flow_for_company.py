import logging
import time

from celery import shared_task
from hdlib.DateTime.Date import Date

from main.apps.account.models import Company
from main.apps.billing.services.aum_fee import AumFeeUpdateService
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider

logger = logging.getLogger(__name__)


@shared_task(
    bind=True, 
    time_limit=15 * 60, 
    max_retries=3,
    name='aum_fee_flow_for_company',
    tags=['eod']  # Add this line
)
def aum_fee_flow_for_company(self, company_id: int):

    start_time = time.time()

    try:
        # Retrieve the company
        company = Company.objects.get(pk=company_id)
        if company.status != Company.CompanyStatus.ACTIVE:
            raise Exception(f"Company (ID:{company_id}) is not active.")

        # Current date and time
        current_time = Date.now()
        logger.debug(f"AUM fee update flow for company (ID={company_id}) at time {current_time}.")

        # Fetch FX spot rates
        fx_provider = FxSpotProvider()
        spot_cache = fx_provider.get_spot_cache(time=current_time)

        # Execute AUM fee update
        AumFeeUpdateService().run_eod(company=company, date=current_time, spot_fx_cache=spot_cache)

        logger.debug("[aum_fee_flow_for_company] AUM fee update executed successfully!")

    except Exception as ex:
        logger.error(f"[aum_fee_flow_for_company] Error while updating AUM fees: {ex}")
        # Reraise the exception to let Celery handle retries or failure logging
        raise
    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"[aum_fee_flow_for_company] Execution time for updating AUM fees: {execution_time} seconds")
        return f"{execution_time / 60} minutes"
