import logging

from main.apps.dataprovider.models.dataprovider import DataProvider
from main.apps.dataprovider.models.profile import Profile
from main.apps.dataprovider.models.source import Source
from main.apps.dataprovider.services.downloader.provider_handler.gcp.gcp_handler import GcpHandler
from main.apps.dataprovider.services.downloader.provider_handler.local.local_handler import LocalHandler
from main.apps.dataprovider.services.downloader.provider_handler.sftp.sftp_handler import SftpHandler

logger = logging.getLogger(__name__)


class DataDownloader(object):
    """
    This class provides the data downloader service by looping through every data provider -> source -> profile.
    """

    def execute(self):
        """ Entry point method for data downloader service"""
        self._process_data_providers()

    def _process_data_providers(self):
        for data_provider in DataProvider.objects.filter(enabled=True):
            for source in data_provider.source_set.filter(enabled=True):
                for profile in source.profile_set.filter(enabled=True):
                    logging.info(f"Downloading profile {profile.pk}")
                    if source.data_type == Source.DataType.GCP:
                        gcp_handler = GcpHandler(profile=profile)
                        gcp_handler.execute()
                    if source.data_type == Source.DataType.LOCAL_STORAGE:
                        local_handler = LocalHandler(profile=profile)
                        local_handler.execute()
                    if source.data_type == Source.DataType.SFTP:
                        sftp_handler = SftpHandler(profile=profile)
                        sftp_handler.execute()
                    else:
                        continue


class DataDownloaderByProfile:
    profile: Profile

    def __init__(self, profile:Profile) -> None:
        self.profile = profile

    def execute(self):
        if self.profile.source.data_type == Source.DataType.GCP:
            self.__download_gcp()
        elif self.profile.source.data_type == Source.DataType.LOCAL_STORAGE:
            self.__download_local()
        elif self.profile.source.data_type == Source.DataType.SFTP:
            self.__download_sftp()
        else:
            pass

    def __download_gcp(self):
        gcp_handler = GcpHandler(profile=self.profile)
        gcp_handler.execute()

    def __download_sftp(self):
        sftp_handler = SftpHandler(profile=self.profile)
        sftp_handler.execute()

    def __download_local(self):
        local_handler = LocalHandler(profile=self.profile)
        local_handler.execute()
