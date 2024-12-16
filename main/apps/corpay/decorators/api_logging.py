import json
import logging
from functools import wraps
from django_context_request import request
from django_context_request.exceptions import RequestContextProxyError
from requests import Response

from main.apps.corpay.models.api_log import ApiRequestLog, ApiResponseLog
from main.apps.corpay.services.api.exceptions import CorPayAPIException

logger = logging.getLogger(__name__)


def log_api(method):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                user = None
                company = None
                try:
                    if request.user is not None and request.user.is_authenticated:
                        user = request.user
                        company = request.user.company
                except RequestContextProxyError.ObjNotFound as e:
                    ...
                except Exception as e:
                    logger.error(e)

                payload = None
                if 'data' in kwargs:
                    payload = kwargs['data'].json()
                try:
                    api_request_log = ApiRequestLog(
                        user=user,
                        company=company,
                        url=kwargs['url'],
                        method=method,
                        payload=payload
                    )
                    api_request_log.save()
                except Exception as e:
                    logger.error(f"Unable to save pre-request log: {e}")
                response = func(*args, **kwargs)
                try:
                    api_response_log = ApiResponseLog(
                        user=user,
                        company=company,
                        request_log=api_request_log,
                        response=response
                    )
                    api_response_log.save()
                except Exception as e:
                    logger.error(f"Unable to save post-request log: {e}")
                return response
            except CorPayAPIException as e:
                response_data = e.args
                if isinstance(e.args[0], Response):
                    response_data = e.args[0].content
                if isinstance(response_data, bytes):
                    response_data = response_data.decode('utf-8')
                api_response_log = ApiResponseLog(
                    user=user,
                    company=company,
                    request_log=api_request_log,
                    response=json.dumps(response_data, indent=4)
                )
                api_response_log.save()
                logger.error(
                    f"Encountered CorPayAPIException when making the request: {e}")
                raise e
            except Exception as e:
                logger.error(f"Unable to log CorPay API Request: {e}")
                raise e

        return wrapper

    return decorator
