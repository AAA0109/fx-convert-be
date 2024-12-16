import logging

from django.core.management.base import BaseCommand, CommandParser
from hdlib.DateTime.Date import Date

from main.apps.core.utils.slack import decorator_to_post_exception_message_on_slack
from main.apps.dataprovider.models import Profile
from main.apps.dataprovider.services.importer.data_importer import DataImporter
# import pdb; pdb.set_trace()

class Command(BaseCommand):
    help = 'Run market data importer'

    def add_arguments(self, parser: CommandParser):
        parser.add_argument('--profile_id')
        parser.add_argument('--ignore_days', type=bool, default=False)
        parser.add_argument('--company_id', type=int, default=None, required=False)
        parser.add_argument('--fxpair_id', type=int, default=None, required=False)

    @decorator_to_post_exception_message_on_slack()
    def handle(self, *args, **options):
        weekday = Date.now(tz=Date.timezone_NY).weekday()
        try:
            ignore_days: bool = options['ignore_days']
            profile_id: int = options['profile_id']
            run_options = {
                "company_id": options['company_id'],
                "fxpair_id": options['fxpair_id']
            }

            logging.info(f"Running market data importer for profile_id={profile_id} (ignore_days={ignore_days}) with following configurations: {run_options}")

            profile = Profile.objects.get(pk=profile_id)
            if ignore_days or profile.days.__contains__(str(weekday)):
                logging.info(f"Importing market data for {profile.name} "
                             f"(profile_id={profile.pk}, ignore_days={ignore_days})")

                data_importer = DataImporter(profile.pk, options=run_options)
                data_importer.execute()

            logging.info("Command executed successfully!")
        except Exception as ex:
            logging.exception(ex)
            raise Exception(ex)
