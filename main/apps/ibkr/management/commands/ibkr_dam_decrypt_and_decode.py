import logging

from django.core.management import BaseCommand
from main.apps.ibkr.services.eca.connector import IBECAConnector


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--data", type=str, help="Required: data to decrypt")

    def handle(self, *args, **options):
        try:
            data = options['data']
            connector = IBECAConnector()
            output = connector.decode_and_decrypt_data(data)
            self.stdout.write(output.decode(('utf8')))
        except Exception as e:
            logging.error(e)
            raise e
