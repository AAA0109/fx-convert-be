import os
import shutil
import re

from datetime import datetime
from django.core.files import File as DjangoFile
from pathlib import Path
from typing import List

from main.apps.dataprovider.models.dataprovider import DataProvider
from main.apps.dataprovider.models.file import File
from main.apps.dataprovider.models.profile import Profile


class ExtractorHandler:
    BASE_TEMP_PATH = f"/tmp"
    profile:Profile
    extract_path:str
    now:str
    unpack_format:str = ''

    def __init__(self, profile: Profile) -> None:
        self.now = datetime.now().strftime("%Y%m%d%H%M%S")
        self.profile = profile
        self.extract_path = f"{self.BASE_TEMP_PATH}.archive/{self.profile.pk}/{self.now}"
        self.unpack_format = self.profile.file_format

        if self.profile.file_format == Profile.FileFormat.TAR_GZ:
            self.unpack_format = 'gztar'

    def __rename_extracted_files(self) -> List[str]:
        extracted_files = os.listdir(self.extract_path)
        renamed_extracted_files = []

        for file in extracted_files:
            splits:List[str] = file.split('.')
            new_filename = f"{splits[0]}_{self.now}.{splits[-1].lower()}"
            os.rename(
                os.path.join(self.extract_path, file),
                os.path.join(self.extract_path, new_filename),
            )
            renamed_extracted_files.append(new_filename)
        return renamed_extracted_files

    def extract_archive(self, local_file_path:str) -> List[str]:
        shutil.unpack_archive(local_file_path, self.extract_path, format=self.unpack_format)
        extracted_files = os.listdir(self.extract_path)

        if self.profile.source.data_provider.provider_handler == DataProvider.ProviderHandlers.FIN_CAL:
            extracted_files = self.__rename_extracted_files()
        return extracted_files

    def get_file_paths(self, profile:Profile, files:List[str]) -> list:
        pattern = re.compile(rf"{profile.filename}\.{profile.file_format}", flags=re.IGNORECASE)
        file_paths = list(filter(pattern.match, files))
        return file_paths

    def extract_and_upload(self, local_file_path:str):
        if self.profile.extract_for_profile_ids:
            extracted_files = self.extract_archive(local_file_path=local_file_path)
            profile_ids = self.profile.extract_for_profile_ids.split(',')

            for id in profile_ids:
                profile:Profile = Profile.objects.get(pk=int(id))
                matched_files = self.get_file_paths(profile=profile, files=extracted_files)
                self.save_file_for_related_profile(profile=profile, matched_files=matched_files)
        pass

    def save_file_for_related_profile(self, profile:Profile, matched_files:List[str]):
        for matched_file in matched_files:
            django_file = None
            saved_file_path = f"{profile.directory}/{matched_file}"
            file_model = File(data_provider=profile.source.data_provider, profile=profile, source=profile.source,
                            file_path=saved_file_path, status=File.FileStatus.QUEUED)
            read_path = f"{self.extract_path}/{matched_file}"
            profile_files = File.objects.filter(file_path=saved_file_path, profile=self.profile)

            if profile_files.exists():
                file_model = File.objects.filter(file_path=saved_file_path, profile=self.profile).first()
                django_file = file_model.file

            if not profile_files.exists():
                file_model = File(data_provider=profile.source.data_provider, profile=profile, source=profile.source,
                                file_path=saved_file_path, status=File.FileStatus.QUEUED, file=django_file)
                file_model.save()

                if django_file is None:
                    path = Path(read_path)

                    with path.open(mode='rb') as f:
                        file_model.file = DjangoFile(f, name=path.name)
                        file_model.status = File.FileStatus.DOWNLOADED
                        file_model.save()
                else:
                    file_model.status = File.FileStatus.DOWNLOADED
                    file_model.save()
