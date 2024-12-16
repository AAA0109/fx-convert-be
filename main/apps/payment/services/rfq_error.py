import traceback
from typing import List
from django.conf import settings
from rest_framework import status


class RfqErrorProvider:

    @staticmethod
    def generate_response(exception:Exception):
        resp = {
            "error": f"{exception}"
        }
        if settings.DEBUG:
            tb = ''.join(traceback.format_exception(None, exception, exception.__traceback__))
            resp["traceback"] = f"{tb}"
            resp['traceback'] = f"{tb}"

        return resp

    @staticmethod
    def get_status_code(serialized_response:dict):
        if  len(serialized_response.get('failed', [])) > 0 or len(serialized_response.get('error', [])) > 0:
            return status.HTTP_400_BAD_REQUEST
        return status.HTTP_200_OK
