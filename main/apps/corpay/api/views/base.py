from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from main.apps.broker.models import Broker
from main.apps.corpay.services.api.exceptions import BadRequest, NotFound, Forbidden, Gone, InternalServerError
from main.apps.corpay.services.corpay import CorPayService


class CorPayBaseView(APIView):
    permission_classes = (IsAuthenticated,)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.corpay_service = CorPayService()
        self._broker = None

    @property
    def broker(self):
        if self._broker is None:
            self._broker = Broker.objects.get(name='Corpay')
        return self._broker

    def handle_exception(self, exc):
        if isinstance(exc, BadRequest):
            exc.status_code = status.HTTP_400_BAD_REQUEST
        elif isinstance(exc, NotFound):
            exc.status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, Forbidden):
            exc.status_code = status.HTTP_403_FORBIDDEN
        elif isinstance(exc, Gone):
            exc.status_code = status.HTTP_410_GONE
        elif isinstance(exc, InternalServerError):
            exc.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        exception_handler = self.get_exception_handler()
        context = self.get_exception_handler_context()
        response = exception_handler(exc, context)
        if response is None:
            return super().handle_exception(exc)
        return response
