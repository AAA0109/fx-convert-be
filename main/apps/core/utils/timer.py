# Create your tests here.

import datetime
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def timer(logger):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = str(datetime.timedelta(seconds=end_time - start_time))
            logger.debug(f"{func.__name__} took {duration} seconds to execute")
            return result

        return wrapper

    return decorator
