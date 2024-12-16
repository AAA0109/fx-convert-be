import logging
import re
import os
from pathlib import Path
import pysftp

from django.core.files import File as DjangoFile

from main.apps.dataprovider.services.downloader.provider_handler.handler import Handler
from main.apps.dataprovider.models import (
    Profile,
    File
)
from main.apps.dataprovider.services.extractor.extractor_handler import ExtractorHandler

logger = logging.getLogger(__name__)


class SftpHandler(Handler):
    sftp = None

    def __init__(self, profile: Profile):
        super().__init__(profile=profile)
        source = profile.source
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        try:
            self.sftp = pysftp.Connection(source.sftp_host, username=source.sftp_username,
                                      password=source.sftp_password, port=source.sftp_port,
                                      cnopts=cnopts)
        except Exception as e:
            logger.error(f"{e.with_traceback(e.__traceback__)}")

    def __del__(self):
        if self.sftp:
            self.sftp.close()

    def execute(self):
        if not self.sftp:
            return
        return super().execute()

    def get_file_paths(self) -> list:
        source = self.profile.source
        files = self.sftp.listdir(source.sftp_dir)
        pattern = re.compile(rf"{self.profile.filename}\.{self.profile.file_format}", flags=re.IGNORECASE)
        file_paths = list(filter(pattern.match, files))
        return file_paths

    def download_files(self, file_paths: list):
        file_pattern = re.compile(rf".*{self.profile.filename}\.{self.profile.file_format}", flags=re.IGNORECASE)
        file_paths = list(filter(file_pattern.match, file_paths))
        for filename in file_paths:
            saved_file_path = f"{self.profile.directory}/{filename}"
            download_file_path = f"{self.profile.source.sftp_dir}/{filename}"
            self.download_file(filename=filename, download_file_path=download_file_path,
                               saved_file_path=saved_file_path)
        pass

    def download_file(self, filename: str, download_file_path: str, saved_file_path: str):
        data_provider = self.profile.source.data_provider
        source = self.profile.source
        django_file = None
        local_file_directory = self.get_local_file_directory()
        local_file_path = f"{local_file_directory}/{filename}"
        if File.objects.filter(file_path=saved_file_path, profile=self.profile).exists():
            file_model = File.objects.filter(file_path=saved_file_path, profile=self.profile).first()
            django_file = file_model.file
        if not File.objects.filter(file_path=saved_file_path, profile=self.profile).exists():
            if not (os.path.exists(local_file_directory)):
                os.makedirs(local_file_directory)
            self.sftp.get(download_file_path, local_file_path)
            file_model = File(data_provider=data_provider, profile=self.profile, source=source,
                              file_path=saved_file_path, status=File.FileStatus.QUEUED, file=django_file)
            file_model.save()
            if django_file is None:
                path = Path(local_file_path)
                with path.open(mode='rb') as f:
                    file_model.file = DjangoFile(f, name=path.name)
                    file_model.status = File.FileStatus.DOWNLOADED
                    file_model.save()
            else:
                file_model.status = File.FileStatus.DOWNLOADED
                file_model.save()

            # Extract archive file and assign extracted files to each related profile
            if self.profile.file_format == Profile.FileFormat.TAR_GZ or self.profile.file_format == Profile.FileFormat.ZIP:
                extractor = ExtractorHandler(profile=self.profile)
                extractor.extract_and_upload(local_file_path=local_file_path)

    def get_local_file_directory(self) -> str:
        if self.profile.file_format == Profile.FileFormat.TAR_GZ:
            return f"{self.TAR_GZ_PATH}/{self.profile.directory}"
        elif self.profile.file_format == Profile.FileFormat.ZIP:
            return f"{self.ZIP_PATH}/{self.profile.directory}"
        return f"{self.CSV_PATH}/{self.profile.directory}"
