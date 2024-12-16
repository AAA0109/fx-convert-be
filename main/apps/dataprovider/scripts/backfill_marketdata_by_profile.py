import logging

from main.apps.dataprovider.models import File, Profile
from main.apps.dataprovider.services.importer.data_importer import DataImporter


def _process_csv(self):
    query_set = File.objects.filter(
        status__in=[File.FileStatus.DOWNLOADED, File.FileStatus.ERROR, File.FileStatus.PREPROCESSED],
        profile__enabled=True,
        source__enabled=True,
        data_provider__enabled=True,
        profile__file_format=Profile.FileFormat.CSV,
        profile__target__isnull=False
    )
    if self.profile_id is not None:
        query_set = query_set.filter(profile_id=self.profile_id)
    for downloaded_file in query_set:
        profile = downloaded_file.profile
        logging.info(f"Starting import for profile: {profile.id}")
        try:
            downloaded_file.status = File.FileStatus.PREPROCESSING
            downloaded_file.save()
            fpath = self._get_filepath(downloaded_file, 'csv')
            self._import_csv(fpath=fpath, profile=profile)
            downloaded_file.status = File.FileStatus.PREPROCESSED
            downloaded_file.save()
        except Exception as e:
            downloaded_file.status = File.FileStatus.ERROR
            downloaded_file.save()
            logging.error(e)
            raise e


DataImporter._process_csv = _process_csv


def run(*args):
    profile_id = int(args[0])
    profile = Profile.objects.get(pk=profile_id)
    logging.info(f"Backfill for {profile.name}")
    run_options = {
        "company_id": None,
        "fxpair_id": None
    }
    data_importer = DataImporter(profile.pk, options=run_options)
    data_importer.execute()
    logging.info("Command executed successfully!")
