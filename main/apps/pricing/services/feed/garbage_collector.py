import time
from datetime import datetime, timedelta

from hdlib.AppUtils.log_util import get_logger, logging

from main.apps.dataprovider.services.collectors.adapters.price_feed import PriceFeedFactory
from main.apps.pricing.models import Feed

logger = get_logger(level=logging.INFO)


class GarbageCollectionService(object):
    _TIME_TO_LIVE = timedelta(minutes=30)

    def execute(self):
        zero_subscriber_feed_times = {}
        while True:
            feeds = Feed.objects.all()
            now = datetime.now()
            for feed in feeds:
                price_feed = PriceFeedFactory.create_price_feed(feed_id=feed.id, mode='garbage_collect')
                total_subscriber = price_feed.count_subscriber()

                if total_subscriber == 0:
                    if feed.id not in zero_subscriber_feed_times:
                        zero_subscriber_feed_times[feed.id] = now
                        logger.info(f"Feed {feed} has no subscriber. Monitoring started.")
                    elif now - zero_subscriber_feed_times[feed.id] >= self._TIME_TO_LIVE:
                        feed.delete()
                        del zero_subscriber_feed_times[feed.id]
                        logger.info(f"Feed {feed} has been deleted after 30 minutes of no subscribers.")
                else:
                    if feed.id in zero_subscriber_feed_times:
                        del zero_subscriber_feed_times[feed.id]
                        logger.info(f"Feed {feed} now has {total_subscriber} subscriber(s), stopped monitoring.")

                logger.info(f"Feed {feed} has {total_subscriber} subscriber(s).")

            time.sleep(2.0)  # Loop every 2 seconds
