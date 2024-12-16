import logging
from hdlib.DateTime.Date import Date

from main.apps.account.models import Company
from main.apps.corpay.models import Forward
from main.apps.corpay.services.corpay import CorPayExecutionService

logger = logging.getLogger(__name__)


class DrowdownService:
    def __init__(self, corpay_service: CorPayExecutionService):
        self._corpay_service = corpay_service

    def draw_down(self, date: Date, company: Company):
        for forward in Forward.get_drawdown_forwards(date=date, company=company):
            forward_id = forward.id
            logger.debug(f"Draw down forward (ID={forward_id})")
            forward = self._corpay_service.drawdown_forward(forward)
            if forward is None:
                logger.error(f"Forward (ID={forward_id}) drawdown unsuccessfully")
                continue
            if forward.drawdown_order_number is not None:
                logger.debug(f"Forward (ID={forward_id}) drawndown successfully")
                forward.drowdown_date = date
                logger.debug(f"Updating forward (ID={forward_id}) drowdown date to {date}")
                forward.save()
            else:
                logger.error(f"Forward (ID={forward_id}) drawdown unsuccessfully")
