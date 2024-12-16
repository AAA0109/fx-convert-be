import redis
from croniter import croniter
from datetime import datetime
import pytz
from django.core.cache.backends.base import BaseCache

class RedisCronCache(BaseCache):
    """
    This is a django-cache replacement that uses
    redis but also supports cron-syntax for setting
    expiry schedules.
    """
    def __init__(self, params):
        super().__init__(params)
        self.redis_url = params.get('REDIS_URL')
        self.redis_client = redis.Redis(connection_pool=redis.ConnectionPool.from_url(self.redis_url))
        self.default_ttl = params.get('DEFAULT_TIMEOUT', 300)  # default TTL in seconds
        self.default_timezone = pytz.timezone(params.get('TIMEZONE', 'UTC'))

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        self.set(key, value, timeout, version)

    # TODO: error handling
    
    def get(self, key, default=None, version=None):
        value = self.redis_client.get(key)
        if value is None:
            return default
        return value

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, timezone=None, version=None):
        if isinstance(timeout, str):
            timeout = self._calculate_ttl_from_cron(timeout, timezone or self.default_timezone)
        if timeout is None:
            timeout = self.default_ttl
        self.redis_client.setex(key, timeout, value)

    def delete(self, key, version=None):
        self.redis_client.delete(key)

    def clear(self):
        ... # do not allow this

    def _calculate_ttl_from_cron(self, cron_expression, timezone):
        now = datetime.now(timezone)
        cron = croniter(cron_expression, now)
        next_time = cron.get_next(datetime)
        ttl = (next_time - now).total_seconds()
        return int(ttl)

