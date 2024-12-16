import logging
import redis

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# ========

class CACHE_FORMATS:
    JSON = 'json'
    AVRO = 'avro'
    PICKLE = 'pickle'

# ========

class RedisCache:
    conn = {}

    def __init__(self, cache_endpoint=None, data_type=CACHE_FORMATS.JSON, use_worker=False):
        self.data_type = data_type
        self.cache_endpoint = cache_endpoint if cache_endpoint else (settings.REDIS_URL if use_worker else settings.REDIS_WORKER_URL)

    def ensure_conn(self):
        try:
            return self.conn[self.cache_endpoint]
        except KeyError:
            lconn = redis.Redis.from_url(self.cache_endpoint)
            RedisCache.conn[self.cache_endpoint] = lconn
            return lconn

    def get_key(self, bucket, key):
        return f'{settings.APP_ENVIRONMENT}.{bucket}'

    def write_record(self, record, bucket, key, data=None):
        logger.info(f'write record to cache bucket: {bucket}')
        if not self.cache_endpoint: 
            logger.error('No Redis endpoint specified.')
            return
        
        if not data:
            if self.data_type == CACHE_FORMATS.JSON:
                data = record.export_to_json().encode()
            else:
                raise ValueError(f'Unsupported data format: {self.data_type}')
        if data:
            conn = self.ensure_conn()
            rkey = self.get_key(bucket, key)
            try:
                conn.set(rkey, data)
            except redis.RedisError as e:
                logger.error(f'Failed to write to Redis: {e}')

    def read_record(self, bucket, key):
        logger.info(f'read record from cache bucket: {bucket}')
        if not self.cache_endpoint:
            logger.error('No Redis endpoint specified.')
            return None
        
        conn = self.ensure_conn()
        rkey = self.get_key(bucket, key)
        try:
            data = conn.get(rkey)
            if data:
                return data
            else:
                logger.info(f'Cache miss for {rkey}')
                return None
        except redis.RedisError as e:
            logger.error(f'Failed to read from Redis: {e}')
            return None

# ========

class DjangoCache:

    def __init__(self, data_type=CACHE_FORMATS.JSON):
        self.data_type = data_type

    def get_key(self, bucket, key):
        return f'{settings.APP_ENVIRONMENT}.{bucket}'

    def write_record(self, record, bucket, key, data=None):
        logger.info(f'write record to Django cache bucket: {bucket}, key: {key}')

        if not data:
            if self.data_type == CACHE_FORMATS.JSON:
                data = record.export_to_json().encode()
            else:
                raise ValueError(f'Unsupported data format: {self.data_type}')
            
        if data:
            rkey = self.get_key(bucket, key)
            try:
                cache.set(rkey, data)
            except Exception as e:
                logger.error(f'Failed to write to Django cache: {e}')

    def read_record(self, bucket, key):
        logger.info(f'Reading record from Django cache bucket: {bucket}, key: {key}')

        rkey = self.get_key(bucket, key)
        try:
            data = cache.get(rkey)
            if data:
                return data
            else:
                logger.info(f'Cache miss for {rkey}')
                return None
        except Exception as e:
            logger.error(f'Failed to read from Django cache: {e}')
            return None

if __name__ == "__main__":
    import django

    django.setup()

    red = RedisCache()
