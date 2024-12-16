import logging
from functools import wraps

from django.core.cache import cache

import hashlib

logger = logging.getLogger(__name__)


def redis_func_cache(key: str = None, timeout: int = None, delete: bool = False):
    """
    A decorator that provides caching functionality for functions that may be expensive to run.

    :param key: A string representing the cache key for the function. If not provided, the function name and arguments will be used to generate a unique key.
    :param timeout: An integer representing the time in seconds that the result of the function should be cached for. If not provided, the result will be cached indefinitely.
    :param delete: A boolean indicating whether the cache for the function should be deleted before running the function.

    :return: A decorator function that can be used to decorate other functions.

    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Exclude 'self' parameter if present
            args_without_self = args[1:] if args and args[0] is not None else args
            try:
                cache_key = key if key is not None else hashlib.md5(
                    f"{func.__name__}:{args_without_self}:{kwargs}".encode()
                ).hexdigest()
                logger.debug(f"redis_func_cache - cache_key='{cache_key}'")

                if delete:
                    logger.debug(f"redis_func_cache - Deleting cache - cache_key='{cache_key}'")
                    cache.delete(cache_key)
                    logger.debug(f"redis_func_cache - Cache deleted - cache_key='{cache_key}'")

                logger.debug(f"redis_func_cache - Getting cache - cache_key='{cache_key}'")
                result = cache.get(cache_key)
                if result is not None:
                    logger.debug(f"redis_func_cache - Cache hit - cache_key='{cache_key}'")
                    return result

                logger.debug(f"redis_func_cache - Cache miss - cache_key='{cache_key}'")
                logger.debug(
                    f"redis_func_cache - Calling func - func='{func.__name__}', args='{args}', kwargs='{kwargs}'")
                result = func(*args, **kwargs)

                logger.debug(f"redis_func_cache - Setting cache - cache_key='{cache_key}', timeout='{timeout}'")
                cache.set(cache_key, result, timeout=timeout)
            except Exception as ex:
                logger.warning(f"redis_func_cache - Unable to create cache - {ex.__str__()}'")
                result = func(*args, **kwargs)

            return result

        return wrapper

    return decorator
