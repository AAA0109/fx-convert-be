from django.core.management.base import BaseCommand
from main.apps.dataprovider.services.downloader.data_downloader import DataDownloader


class Command(BaseCommand):
    help = 'Run market data importer'

    def handle(self, *args, **options):
        try:
            data_downloader = DataDownloader()
            data_downloader.execute()

            print("Command executed successfully!")
        except Exception as ex:
            print(ex)
            raise Exception(ex)
