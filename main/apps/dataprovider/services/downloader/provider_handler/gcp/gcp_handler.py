import re
import logging
from pathlib import Path

from django.core.files import File as DjangoFile
from django.conf import settings
from storages.backends.gcloud import GoogleCloudStorage

from main.apps.dataprovider.services.downloader.provider_handler.handler import Handler
from main.apps.dataprovider.models import (
    File,
    Profile
)

logger = logging.getLogger(__name__)


class GcpHandler(Handler):
    gcp_path = f"{settings.GS_DATA_PATH}csv"
    storage = None

    def get_file_paths(self) -> list:
        self.storage = GoogleCloudStorage()
        if self.profile.file_format == Profile.FileFormat.JSON:
            self.gcp_path = f"{settings.GS_DATA_PATH}json"
        elif self.profile.file_format == Profile.FileFormat.XLSX:
            self.gcp_path = f"{settings.GS_DATA_PATH}xlsx"
        else:
            self.gcp_path = f"{settings.GS_DATA_PATH}csv"
        path = f"{self.gcp_path}/{self.profile.directory}"
        logger.debug(f"Listing files from GCP storage path: {path}")
        filenames, file_paths = self.storage.listdir(path)
        return file_paths

    def download_files(self, file_paths: list):
        pattern = re.compile(rf"{self.profile.filename}\.{self.profile.file_format}")
        gcp_file_paths = set(filter(pattern.match, file_paths))

        # Append the GCP path and profile directory to each GCP file path
        full_gcp_paths = {f"{self.profile.directory}/{path}" for path in gcp_file_paths}

        # Get existing file paths from the database for this specific profile
        existing_file_paths = set(File.objects.filter(
            profile=self.profile
        ).values_list('file_path', flat=True))

        # Find new files to download
        new_files = full_gcp_paths - existing_file_paths

        for filename in new_files:
            download_file_path = f"{self.gcp_path}/{filename}"
            saved_file_path = f"{filename}"
            logger.debug(f"Downloading new file for profile {self.profile.id}: {filename}")
            self.download_file(filename=filename, download_file_path=download_file_path,
                               saved_file_path=saved_file_path)

    def download_file(self, filename: str, download_file_path: str, saved_file_path: str):
        data_provider = self.profile.source.data_provider
        source = self.profile.source
        django_file = None
        if File.objects.filter(file_path=saved_file_path, profile=self.profile).exists():
            logger.debug(f"File already exist, skipping")
            file_model = File.objects.filter(file_path=saved_file_path, profile=self.profile).first()
            django_file = file_model.file
        if not File.objects.filter(file_path=saved_file_path, profile=self.profile).exists():
            file_model = File(data_provider=data_provider, profile=self.profile, source=source,
                              file_path=saved_file_path, status=File.FileStatus.QUEUED, file=django_file)
            file_model.save()
            if django_file is None:
                logger.debug(f"File is new, starting download")
                path = Path(saved_file_path)
                with self.storage.open(download_file_path) as f:
                    file_model.file = DjangoFile(f, name=path.name)
                    file_model.status = File.FileStatus.DOWNLOADED
                    file_model.save()
            else:
                file_model.status = File.FileStatus.DOWNLOADED
                file_model.save()
            logger.debug(f"Download complete!")
