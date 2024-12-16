import logging

from django.core.management.base import BaseCommand

from main.apps.pricing.services.feed.garbage_collector import GarbageCollectionService


class Command(BaseCommand):
    help = 'Garbage collect Feed.'

    def handle(self, *args, **options):
        try:
            garbage_collector = GarbageCollectionService()
            garbage_collector.execute()
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
