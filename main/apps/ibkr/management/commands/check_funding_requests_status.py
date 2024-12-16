from __future__ import annotations

import logging
from typing import Any

from django.core.management.base import BaseCommand
from hdlib.DateTime.Date import Date

from main.apps.ibkr.models.fb import FundingRequest
from main.apps.ibkr.services.eca.eca import IBECAService
from main.apps.ibkr.services.fb.fb import IBFBService
from main.apps.core.utils.slack import SlackNotification

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Django command to loop through all funding requests not in terminal status and get the most recent status"


    def __init__(self):
        self.slack = SlackNotification()
    def handle(self, *args: Any, **options: Any) -> str | None:

        ib_eca_service = IBECAService()
        if ib_eca_service.healthcheck():
            logger.debug("IB WS healthcheck passed")
        else:
            logger.error("IB WS healthcheck failed, skipping funding request check")
            return

        logging.info("IB WS is healthy refreshing funding requests statuses...")
        ib_fb_service = IBFBService()
        today = Date.today()
        days_back = 27
        date = today - days_back

        logger.debug("Getting a list of updated upload ids")
        updated_ids = ib_fb_service.get_updated_upload_ids(date)
        if len(updated_ids) > 0:
            for updated_id in updated_ids:
                try:
                    ib_fb_service.get_status(updated_id)
                except Exception as e:
                    logging.error(e)
                    thread_ts = self.slack.send_text_message(
                        text=f"Failed to update funding request for[{updated_id})]. "
                    )
                    self.slack.send_mrkdwn_message(
                        text="Exception",
                        mrkdwn=f"```{e}```",
                        thread_ts=thread_ts
                    )
        else:
            logger.debug("No uploaded ids were updated")
