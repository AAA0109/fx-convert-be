import logging

from django.core.management.base import BaseCommand

from main.apps.pricing.services.feed.run_feeds import RunFeedService

logger = logging.getLogger("root")


class Command(BaseCommand):
    help = 'Run Price Feeds.'

    def handle(self, *args, **options):
        try:
            run_feeds = RunFeedService()
            run_feeds.execute()
            logging.info("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
