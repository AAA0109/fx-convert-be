import os
import tempfile
from abc import ABC
from datetime import timedelta
from datetime import timezone
from enum import Enum
from typing import Union, Dict

import pandas as pd
from django.conf import settings
from django.utils import timezone
from google.cloud import storage
from hdlib.DateTime.Date import Date


class PlatformReportingService(ABC):
    class Frequency(Enum):
        DAILY = 'DAILY'
        WEEKLY = 'WEEKLY'
        MONTHLY = 'MONTHLY'

    class ReportType(Enum):
        CSV = 'CSV'
        XLSX = 'XLSX'

    report_name: str = None
    report_output_type: ReportType = None
    frequency: Frequency = None
    start_date: Date = None
    end_date: Date = timezone.now()

    def __init__(
        self,
        report_name: str,
        frequency: Frequency,
        report_output_type: ReportType = ReportType.CSV,
        start_date: Date = None,
        end_date: Date = timezone.now(),
    ):
        self.report_name = report_name
        self.frequency = frequency
        self.report_output_type = report_output_type

        if not start_date:
            if self.frequency == PlatformReportingService.Frequency.DAILY:
                start_date = timezone.now() - timedelta(days=1)
            elif self.frequency == PlatformReportingService.Frequency.WEEKLY:
                start_date = timezone.now() - timedelta(weeks=1)
            elif self.frequency == PlatformReportingService.Frequency.MONTHLY:
                start_date = timezone.now() - timedelta(days=30)
            else:
                raise ValueError(f"Unsupported frequency: {frequency}")

        self.start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        self.end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

    def get_data(self) -> Union[pd.DataFrame | Dict[str, pd.DataFrame]]:
        raise NotImplemented

    def generate_report(self):
        data: Union[pd.DataFrame | Dict[str, pd.DataFrame]] = self.get_data()
        file_name: str = (f"{self.start_date.strftime('%Y-%m-%d_%H-%M')}__"
                          f"{self.end_date.strftime('%Y-%m-%d_%H-%M')}."
                          f"{self.report_output_type.value.lower()}")
        output_file: Union[str | None] = None

        if self.report_output_type == PlatformReportingService.ReportType.CSV:
            output_file: str = self.download_csv(
                df=data[0],
                file_name=file_name
            )
        elif self.report_output_type == PlatformReportingService.ReportType.XLSX:
            output_file: str = self.download_excel(
                data=data,
                file_name=file_name
            )

        self.upload_csv_to_gcs(
            file_path=output_file,
            gcs_bucket_path=f"reports/{self.frequency.value}/{self.report_name}/{file_name}"
        )

    @staticmethod
    def download_excel(
        data: Dict[str, pd.DataFrame],
        file_name: str,
        output_dir: str = None
    ) -> str:
        # Use the current directory if no output directory is provided
        if output_dir is None:
            output_dir = tempfile.mkdtemp()

        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Define the full path to the output file
        output_path = os.path.join(output_dir, file_name)

        # Create a Pandas Excel writer using XlsxWriter as the engine
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            for sheet_name, df in data.items():
                # Convert timezone-aware datetimes to timezone-naive
                for col in df.columns:
                    if pd.api.types.is_datetime64tz_dtype(df[col]):
                        df[col] = df[col].dt.tz_convert(None)
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        return output_path

    @staticmethod
    def download_csv(
        df: pd.DataFrame,
        file_name: str,
        output_dir: str = None
    ) -> str:
        # Use a temporary directory if none is provided
        if output_dir is None:
            output_dir = tempfile.mkdtemp()

        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Define the full path to the output file
        output_path = os.path.join(output_dir, file_name)

        # Save the DataFrame to a CSV file at the specified path
        df.to_csv(
            path_or_buf=output_path,
            sep=',',  # Field delimiter for the output file (default is comma)
            na_rep='',  # Missing data representation
            float_format=None,  # Format string for floating point numbers
            columns=None,  # Columns to write (default is to write all columns)
            header=True,  # Write out column names (default True)
            index=False,  # Write row names (index)
            index_label=None,  # Column label for index column(s) if desired
            mode='w',  # Python write mode, default 'w'
            encoding=None,  # Encoding for text data
            compression='infer',  # Compression mode
            quoting=None,  # Controls CSV quoting behavior
            quotechar='"',  # Character to use to quote fields
            line_terminator='\n',  # Newline character or character sequence to use in the output file
            chunksize=None,  # Number of rows to write at a time
            date_format=None,  # Format string for datetime objects
            doublequote=True,  # Control quoting of quotechar inside a field
            escapechar=None,  # Character used to escape other characters
            decimal='.'  # Decimal separator
        )

        # Return the path to the saved CSV file
        return output_path

    @staticmethod
    def upload_csv_to_gcs(
        file_path: str,
        gcs_bucket_path: str,
        gcs_bucket_name: str = settings.GS_BUCKET_NAME,
    ):
        storage_client = storage.Client()
        bucket = storage_client.bucket(gcs_bucket_name)
        blob = bucket.blob(gcs_bucket_path)
        blob.upload_from_filename(file_path)
