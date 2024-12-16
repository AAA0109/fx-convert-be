import logging

from google.cloud import pubsub_v1
from google.api_core.exceptions import AlreadyExists

from django.conf import settings

logger = logging.getLogger(__name__)

# ==================================

class PUB_FORMATS:
    JSON = 'json'
    AVRO = 'avro'
    PICKLE = 'pickle'


class BasePublisher:
    def __init__(self, data_type=PUB_FORMATS.JSON, proj_id=settings.APP_ENVIRONMENT, ):
        self.data_type = data_type
        self.proj_id = proj_id

    def write_record(self, record, bucket, key, data=None):
        logger.info('write record to topic: {self.proj_id} {bucket}')


# ==================================

class GcpPubSub(BasePublisher):
    publisher = None

    def __init__(self, data_type=PUB_FORMATS.JSON, use_cb=False):
        self.data_type = data_type
        self.use_cb = use_cb
        self.project_id = settings.GCP_PROJECT_ID
        if not self.project_id:
            raise ValueError("No GCP_PROJECT_ID set.")
        self.topics = set()

    def done_callback(self, future):
        try:
            message_id = future.result()
            logger.info(f"Message has been published with ID: {message_id}")
        except Exception as e:
            logger.debug(f"An error occurred: {e}")

    @classmethod
    def ensure_client(cls):
        if not cls.publisher:
            cls.publisher = pubsub_v1.PublisherClient()
        return cls.publisher

    def get_topic(self, record, bucket, key):
        self.ensure_client()
        topic_id = f'{settings.APP_ENVIRONMENT}.{bucket}'
        topic_name = self.publisher.topic_path(self.project_id, topic_id)
        if topic_name not in self.topics:
            self.ensure_client()
            try:
                logger.info(f'creating topic: {topic_name}')
                topic = self.publisher.create_topic(name=topic_name)
            except AlreadyExists:
                pass
            self.topics.add(topic_name)
        return topic_name

    def write_record(self, record, bucket, key, data=None, content_type=None):
        if not data:
            if self.data_type == PUB_FORMATS.JSON:
                data = record.export_to_json().encode()
                content_type = PUB_FORMATS.JSON
            else:
                raise ValueError('Unknown data data')
        topic = self.get_topic(record, bucket, key)
        if data and topic:
            logger.info(f'publishing to gcp: {topic} {data}')
            future = self.publisher.publish(topic, data, content_type=content_type)
            # ordering_key=ordering_key, also need to enable ordering
            # without a callback, there is no guarantee that something delivered
            # but this is better for high-throughput
            if self.use_cb: future.add_done_callback(self.done_callback)
