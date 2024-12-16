import datetime
from typing import List
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from main.apps.core.utils.api import HasCompanyAssociated

from main.apps.payment.api.serializers.calendar import (
    ValueDateCalendarRequestSerializer,
    ValueDateCalendarResponseSerializer
)
from main.apps.payment.services.calendar import ValueDateCalendarProvider
from main.apps.oems.backend.calendar_utils import contains

class ValueDateCalendarAPIView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        request=ValueDateCalendarRequestSerializer,
        responses={
            status.HTTP_200_OK: ValueDateCalendarResponseSerializer
        }
    )
    def post(self, request):

        # TODO: we need to get the company from request.user.company
        # then parse the max tenor across all brokers
        # this will determine which broker we can use
        # if broker is provided... set max tenor that way

        serializer = ValueDateCalendarRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # TODO: set max date by company and instrument
        pair = serializer.validated_data.get('pair')
        market = pair.market

        min_date = None # look up if there is a faster-than-spot provider
        max_date = None # look up max tenor by company

        # ccy1, ccy2 = market[:3], market[3:]
        # if ccy1 in ['GBP','USD','CAD','EUR','MXN','AUD']:
        
        if contains(market, ['GBP','USD','CAD','EUR','MXN']):
            # can only do forward against these currencies for now
            spot_only = False
        else:
            spot_only = True

        provider = ValueDateCalendarProvider(
            pair=pair,
            start_date=serializer.validated_data.get('start_date'),
            end_date=serializer.validated_data.get('end_date'),
            spot_only=spot_only,
            # expedited=True if company has nium perms for currency,
            # max_date if company + pair has max tenor
        )
        value_date_calendar = provider.populate_value_dates()

        resp_data =  ValueDateCalendarResponseSerializer(value_date_calendar)
        return Response(resp_data.data, status=status.HTTP_200_OK)
