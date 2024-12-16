from typing import List
from rest_framework import status
from rest_framework.response import Response


class BatchResponseProvider:

    @staticmethod
    def generate_response(serialized_response:dict) -> List[dict]:
        error_codes = []
        if 'executions' in serialized_response.keys():
            for response in serialized_response['executions']:
                for error in response['execution_status']['error']:
                    error_codes.append(str(error['code']))
        elif 'rfqs' in serialized_response.keys():
            for response in serialized_response['rfqs']:
                for error in response['rfq_status']['failed']:
                    error_codes.append(str(error['code']))

        code_join = ','.join(error_codes)
        status_code = status.HTTP_200_OK
        if status.HTTP_500_INTERNAL_SERVER_ERROR in error_codes:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        elif '40' in code_join or '41' in code_join or '42' in code_join:
            status_code = status.HTTP_400_BAD_REQUEST
        return Response(data=serialized_response, status=status_code)
