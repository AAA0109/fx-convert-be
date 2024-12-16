import traceback
from django.conf import settings
from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail


class PaymentResponseUtils:

    @staticmethod
    def create_traceback_response(e:Exception) -> dict:
        resp = {
            'error': f"{e}"
        }
        if settings.DEBUG:
            tb = ''.join(traceback.format_exception(None, e, e.__traceback__))
            resp['traceback'] = f"{tb}"

        return resp

    @staticmethod
    def create_validation_error_response(e:serializers.ValidationError) -> dict:
        resp = {
            'validation_errors': []
        }

        for key in e.detail.keys():
            if isinstance(e.detail[key], list) and len(e.detail[key]) > 0:
                if isinstance(e.detail[key][0], dict):
                    for item in e.detail[key]:
                        resp['validation_errors'].append(item)
                elif isinstance(e.detail[key][0], ErrorDetail):
                    resp['validation_errors'].append({
                        'field': key,
                        'detail': e.detail[key][0].__str__()
                    })


        if settings.DEBUG:
            tb = ''.join(traceback.format_exception(None, e, e.__traceback__))
            resp['traceback'] = f"{tb}"

        return resp
