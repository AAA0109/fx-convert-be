import re
import os
import glob
from pathlib import Path

from django.core.files import File as DjangoFile

from main.apps.dataprovider.services.downloader.provider_handler.handler import Handler
from main.apps.dataprovider.models import (
    Profile,
    File
)


class LocalHandler(Handler):
    def get_file_paths(self) -> list:
        if self.profile.file_format == "json":
            dir_pattern = f"{self.JSON_PATH}/{self.profile.directory}/*.*"
            file_paths = glob.glob(dir_pattern)
        elif self.profile.file_format == "csv":
            dir_pattern = f"{self.CSV_PATH}/{self.profile.directory}/*.*"
            file_paths = glob.glob(dir_pattern)
        elif self.profile.file_format == "xlsx":
            dir_pattern = f"{self.XLSX_PATH}/{self.profile.directory}/*.xlsx"
            file_paths = glob.glob(dir_pattern)
        return file_paths

    def download_files(self, file_paths: list):
        file_pattern = re.compile(rf".*{self.profile.filename}\.{self.profile.file_format}")
        file_paths = list(filter(file_pattern.match, file_paths))
        for file_path in file_paths:
            path_info = Path(file_path)
            saved_file_path = f"{self.profile.directory}/{path_info.name}"
            filename = path_info.name
            download_file_path = file_path
            self.download_file(filename=filename, download_file_path=download_file_path,
                               saved_file_path=saved_file_path)
        pass

    def download_file(self, filename: str, download_file_path: str, saved_file_path: str):
        data_provider = self.profile.source.data_provider
        source = self.profile.source
        django_file = None
        if File.objects.filter(file_path=saved_file_path, profile=self.profile).exists():
            file_model = File.objects.filter(file_path=saved_file_path, profile=self.profile).first()
            django_file = file_model.file
        if not File.objects.filter(file_path=saved_file_path, profile=self.profile).exists():
            file_model = File(data_provider=data_provider, profile=self.profile, source=source,
                              file_path=saved_file_path, status=File.FileStatus.QUEUED, file=django_file)
            file_model.save()
            if django_file is None:
                path = Path(download_file_path)
                if not (os.path.exists(path)):
                    os.makedirs(path)
                with path.open(mode='rb') as f:
                    file_model.file = DjangoFile(f, name=path.name)
                    file_model.status = File.FileStatus.DOWNLOADED
                    file_model.save()
            else:
                file_model.status = File.FileStatus.DOWNLOADED
                file_model.save()
