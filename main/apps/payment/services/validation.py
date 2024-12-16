from typing import List


class BulkPaymentValidationResponseProvider:

    @staticmethod
    def generate_validation_error_response(validation_errors: List[dict]) -> dict:
        validation_results = []
        for i in range(len(validation_errors)):
            validation_results.append(
                {
                    'row_id': i,
                    'is_valid': validation_errors[i] == {},
                    'error_fields': validation_errors[i]
                }
            )
        return {
            'validation_results': validation_results
        }
