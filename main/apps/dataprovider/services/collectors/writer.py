import datetime
import logging
import os
import random
import string
from collections import deque, defaultdict
from dataclasses import asdict

import fastavro
import pandas as pd
import pyarrow as pa
from django.conf import settings
from google.cloud import bigquery
from google.cloud import storage
from google.cloud.exceptions import NotFound

logger = logging.getLogger(__name__)


# ==================

def avro2parquet_type_convert(field_type):
    if isinstance(field_type, dict):
        if field_type['logicalType'] == 'timestamp-micros':
            arrow_type = pa.timestamp('us')
        else:
            raise ValueError(f"Unsupported Avro type: {field_type}")
    elif field_type == 'string':
        arrow_type = pa.string()
    elif field_type == 'int':
        arrow_type = pa.int32()
    elif field_type == 'long':
        arrow_type = pa.int64()
    elif field_type == 'boolean':
        arrow_type = pa.bool_()
    elif field_type == 'double':
        arrow_type = pa.float64()
    # Add more type conversions as necessary
    else:
        raise ValueError(f"Unsupported Avro type: {field_type}")
    return arrow_type


def avro2bq_type_convert(field_type):
    if isinstance(field_type, dict):
        if field_type['logicalType'] == 'timestamp-micros':
            arrow_type = "TIMESTAMP"
        else:
            raise ValueError(f"Unsupported Avro type: {field_type}")
    elif field_type == 'string':
        arrow_type = "STRING"
    elif field_type == 'int':
        arrow_type = "INTEGER"
    elif field_type == 'long':
        arrow_type = "INTEGER"
    elif field_type == 'boolean':
        arrow_type = "BOOLEAN"
    elif field_type == 'double':
        arrow_type = "FLOAT"
    # Add more type conversions as necessary
    else:
        raise ValueError(f"Unsupported Avro type: {field_type}")
    return arrow_type


# Function to convert Avro schema to PyArrow schema
def avro_schema_to_pyarrow_schema(avro_schema):
    # Implement a conversion based on your specific Avro schema
    # This is a basic example and might need adjustments for complex schemas
    fields = []
    for field in avro_schema['fields']:
        field_type = field['type']
        required = True
        if isinstance(field_type, list):
            if field_type[1] == "null":
                arrow_type = avro2parquet_type_convert(field_type[0])
                required = False
            elif field_type[0] == "null":
                arrow_type = avro2parquet_type_convert(field_type[0])
                required = False
        else:
            arrow_type = avro2parquet_type_convert(field_type)
        fields.append(pa.field(field['name'], arrow_type, nullable=(not required)))
    return pa.schema(fields)


def avro_schema_to_bigquery_schema(avro_schema):
    schema = []
    for field in avro_schema['fields']:
        field_type = field['type']
        required = True
        if isinstance(field_type, list):
            if field_type[1] == "null":
                bq_type = avro2bq_type_convert(field_type[0])
                required = False
            elif field_type[0] == "null":
                bq_type = avro2bq_type_convert(field_type[0])
                required = False
        else:
            bq_type = avro2bq_type_convert(field_type)
        mode = 'REQUIRED' if required else 'NULLABLE'
        schema.append(bigquery.SchemaField(field['name'], bq_type, mode=mode))
    return schema


# ===================

def random_string(n=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


# ===================

def upload_gcp(bucket, key, from_path):
    # this is GCP cloud storage - handle failures? this should be threadsafe
    storage_client = storage.Client()
    bucket = storage_client.bucket(self.bucket)
    blob = bucket.blob(key)
    blob.upload_from_filename(from_path)


# ===================

class AvroFileManager:

    def __init__(self, record, file_slug, bucket, key, directory='/tmp'):

        # file stuff
        self.directory = directory
        self.slug = file_slug
        self.bucket = bucket
        self.key = key
        self.uniq = random_string()

        # internal
        self.avro_path = os.path.join(directory, f'{file_slug}.avro')
        self.avro_schema = record.get_avro_schema()
        self.avro_hdl = None
        self.avro_append = False
        self._open_avro()

    def write_record(self, record):
        if self.avro_append:
            # greedily just write the record
            fastavro.writer(self.avro_hdl, None, [asdict(record)])
        else:
            # If the file is new or empty, write the schema and the record
            fastavro.writer(self.avro_hdl, self.avro_schema, [asdict(record)])
            self.avro_append = True

    def _open_avro(self):
        if self.avro_hdl is None:
            # avro stuff
            mode = 'a+b'  # if os.path.exists(self.avro_path) else 'wb'
            self.avro_hdl = open(self.avro_path, mode)
        # self.avro_append = (self.avro_hdl.tell() != 0)

    def _close_avro(self):
        if self.avro_hdl:
            self.avro_hdl.close()
            self.avro_hdl = None

    # ==================

    def close(self):
        self._close_avro()

    def remove(self, path):
        os.remove(path)

    def upload(self, from_path):
        upload_gcp(self.bucket, f'{self.key}.{self.uniq}.parquet', from_path)

    # ===================

    def rotate(self, delete=False, upload=False, convert=False):

        self._close_avro()

        # convert to parqet ?? shoudl check for size of file and be smart about it
        # this sucks because it is not on-line.

        if convert:
            with open(self.avro_path, 'rb') as af:
                avro_reader = fastavro.reader(af)
                df = pd.DataFrame.from_records([record for record in avro_reader])
                upload_path = os.path.join(self.directory, f'{self.slug}.{self.uniq}.parquet')
                df.to_parquet(upload_path, engine='pyarrow', index=False)
        else:
            upload_path = self.avro_path

        logger.info(f'rotating file from {self.avro_path} to {upload_path} {upload} {delete}')

        if upload:
            self.upload(upload_path)

        if delete:
            self.remove(self.avro_path)

        """
        if False:
            # avro_schema = avro_reader.writer_schema
            # Convert Avro schema to PyArrow schema

            arrow_schema = avro_schema_to_pyarrow_schema(avro_schema)

            # Initialize Parquet writer with the PyArrow schema
            with pq.ParquetWriter(self.parquet_path, arrow_schema) as parquet_writer:
                # Re-open the Avro file for reading records
                with open(self.avro_path, 'rb') as af:
                    avro_reader = fastavro.reader(af)
                    for record in avro_reader:
                        # Convert each record to a PyArrow Table
                        # Note: This simplistic approach assumes the record is a simple dict matching the schema directly
                        breakpoint()
                        table = pa.Table.from_pydict([record], schema=arrow_schema)
                        # Write the table to the Parquet file
                        parquet_writer.write_table(table)
        """


# =====================

class BucketManager:

    def __init__(self, directory='/tmp', rotate=False, upload=False, delete=False, flush_on_close=True,
                 file_manager=AvroFileManager):
        self.directory = directory
        self.rotate = rotate
        self.flush_on_close = flush_on_close
        self.upload = upload
        self.delete = delete
        self.file_manager = AvroFileManager
        self.active = {}
        self.retired = {}

    @staticmethod
    def make_slug(bucket, key):
        return f'{bucket}_{key}'

    def flush(self):
        if not self.retired: return
        for k in list(self.retired.keys()):
            old_writer = self.retired.pop(k)
            if self.rotate:
                old_writer.rotate(delete=self.delete, upload=self.upload)

    def write_record(self, record, bucket: str, key: str):

        if bucket in self.active:
            managers = self.active[bucket]
        else:
            managers = {}
            self.active[bucket] = managers

        if not managers:
            file_slug = self.make_slug(bucket, key)
            writer = self.file_manager(record, file_slug, bucket, key, directory=self.directory)
            managers[key] = writer
        elif key in managers:
            writer = managers[key]
        else:
            for k in list(manager.keys()):
                old_writer = manage.pop(k)
                if self.rotate:
                    old_writer.rotate(delete=self.delete, upload=self.upload)
                else:
                    self.retired[(bucket, k)] = old_writer
            file_slug = self.make_slug(bucket, key)
            writer = self.file_manager(record, file_slug, bucket, key, directory=self.directory)
            managers[key] = writer

        logger.info(f'writing record to local storage: {bucket} {key}')
        writer.write_record(record)

    def close(self):
        for manager in self.active.values():
            for writer in manager.values():
                if self.flush_on_close:
                    writer.rotate(delete=self.delete, upload=self.upload)
                writer.close()


class BigQueryManager:
    client = None

    def __init__(self, directory='/tmp', dataset_id='marketdata', batch_size=100, rotate=False, upload=False,
                 delete=False, flush_on_close=True):
        self.directory = directory
        self.rotate = rotate
        self.flush_on_close = flush_on_close
        self.upload = upload
        self.delete = delete
        self.ensure = set()
        self.rows = defaultdict(deque)
        self.batch_size = batch_size
        self.dataset_id = dataset_id
        self.project_id = settings.GCP_PROJECT_ID
        if not self.project_id:
            raise ValueError("No GCP_PROJECT_ID set.")
        self.ensure_dataset()

    def flush(self):
        if self.rows:
            for table_id, rows in self.rows.items():
                if rows:
                    client = self.ensure_client()
                    errors = client.insert_rows_json(table_id, list(rows))  # Make an API request.
                    if errors:
                        logger.debug("Encountered errors while inserting rows: {}".format(errors))
                    rows.clear()

    @classmethod
    def ensure_client(cls):
        if not cls.client:
            cls.client = bigquery.Client()
        return cls.client

    def get_table_name(self, record):
        # self.table_id = f"{self.project_id}.{self.bq_dataset}.{record.__name__}"
        return f'{self.project_id}.{self.dataset_id}.{settings.APP_ENVIRONMENT}-{record.__class__.__name__}'

    def ensure_dataset(self):
        client = self.ensure_client()
        try:
            client.get_dataset(self.dataset_id)  # Make an API request.
            print("Dataset {} already exists".format(self.dataset_id))
            return
        except NotFound:
            print("Dataset {} is not found".format(self.dataset_id))

        dataset = bigquery.Dataset(f'{self.project_id}.{self.dataset_id}')
        dataset.location = "US"
        # other options
        dataset = client.create_dataset(dataset, timeout=30)

    def ensure_table(self, record, bucket, key):
        t = type(record)
        if t not in self.ensure:  # if record has not been ensured
            self.ensure.add(t)
            table_id = self.get_table_name(record)
            client = self.ensure_client()
            try:
                client.get_table(table_id)  # Make an API request.
                logger.debug(f"Table {table_id} already exists.")
            except NotFound:
                # If the table does not exist, create it.
                bq_schema = avro_schema_to_bigquery_schema(record.get_avro_schema())
                table = bigquery.Table(table_id, schema=bq_schema)
                table.time_partitioning = bigquery.TimePartitioning(
                    field="time")  # defaults to DAY for 10 years of data
                table.clustering_fields = ["source", "instrument"]
                table = client.create_table(table)  # Make an API request.
                logger.info(f"Created table {table.project}.{table.dataset_id}.{table.table_id}")

    def write_record(self, record, bucket: str, key: str):
        self.ensure_table(record, bucket, key)
        table_id = self.get_table_name(record)
        self.rows[table_id].append(record.export_bq())
        if len(self.rows[table_id]) >= self.batch_size:
            logger.info('writing records to bigquery')
            self.flush()

    def close(self):
        if self.flush_on_close:
            self.flush()
