import logging

from django.core.management.base import BaseCommand, CommandParser

from main.apps.dataprovider.services.collectors.adapters.price_feed import PriceFeedFactory


class Command(BaseCommand):
    help = 'Run Price Feed.'

    def add_arguments(self, parser: CommandParser):
        """
        example ./manage.py runfeed --feed_id 1
        """
        parser.add_argument('--feed-id', type=int, help='Feed primary key.')

    def handle(self, *args, **options):
        try:
            price_feed = PriceFeedFactory.create_price_feed(feed_id=options.get('feed_id'))
            price_feed.run()

            logging.info("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
