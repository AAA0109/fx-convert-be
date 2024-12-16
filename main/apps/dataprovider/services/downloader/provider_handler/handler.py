from abc import ABC, abstractmethod
from pathlib import Path

from django.conf import settings
from django.core.files import File as DjangoFile

from main.apps.dataprovider.models import (
    DataProvider,
    Source,
    Profile,
    File
)


class Handler(ABC):
    APP_PATH = str(settings.BASE_DIR.parent)
    STORAGE_PATH = APP_PATH + '/storage'
    CSV_PATH = STORAGE_PATH + '/csv'
    JSON_PATH = STORAGE_PATH + '/json'
    XLSX_PATH = STORAGE_PATH + '/xlsx'
    TAR_GZ_PATH = STORAGE_PATH + '/tar_gz'
    ZIP_PATH = STORAGE_PATH + '/zip'
    profile: Profile = None

    def __init__(self, profile: Profile):
        self.profile = profile
    def execute(self):
        file_paths = self.get_file_paths()
        self.download_files(file_paths=file_paths)
        pass

    def get_file_paths(self):
        return []

    def download_files(self, file_paths: list):
        pass

    @abstractmethod
    def download_file(self, filename: str, download_file_path: str, saved_file_path: str):
        raise NotImplementedError
