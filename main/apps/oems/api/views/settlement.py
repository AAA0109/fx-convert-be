from datetime import date, datetime, timedelta

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from main.apps.core.constants import CURRENCY_HELP_TEXT
from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.currency.models import Currency
from main.apps.currency.models.fxpair import FxPair
from main.apps.marketdata.api.serializers.initial import BestExecutionSerializer
from main.apps.oems.api.utils.response import *
from main.apps.oems.backend.calendar_utils import get_non_settlement_days, get_settlement_days, \
    get_current_mkt_session, get_next_mkt_session, next_valid_settlement_day, prev_valid_settlement_day, \
    is_valid_settlement_day, get_fx_settlement_info, get_fx_spot_info
from main.apps.oems.backend.exec_utils import get_best_execution_status
from main.apps.oems.models import Ticket
from main.apps.oems.services.calendar import CalendarService
from main.apps.payment.api.serializers.calendar import ValueDateCalendarResponseSerializer


class DateRangeSerializer(serializers.Serializer):
    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                 help_text=CURRENCY_HELP_TEXT)
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                help_text=CURRENCY_HELP_TEXT)
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs):
        if False and attrs['end_date'] > date.today() + timedelta(years=1, days=1):
            raise serializers.ValidationError("End date beyond calendar scope. Use null to get maximum date.")
        fxpair = FxPair.get_pair_from_currency(attrs.get('sell_currency'), attrs.get('buy_currency'))
        attrs['market_name'] = fxpair.market
        return attrs


class SingleDaySerializer(serializers.Serializer):
    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                 help_text=CURRENCY_HELP_TEXT)
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                help_text=CURRENCY_HELP_TEXT)
    date = serializers.DateField(required=True)

    def validate(self, attrs):
        # comp_date = date(attrs['date'].year, attrs['date'].month, attrs['date'].day)
        if False and comp_date > date.today() + timedelta(days=365):
            raise serializers.ValidationError("Date beyond calendar scope")
        fxpair = FxPair.get_pair_from_currency(attrs.get('sell_currency'), attrs.get('buy_currency'))
        attrs['market_name'] = fxpair.market
        return attrs


class SingleDateTimeSerializer(serializers.Serializer):
    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                 help_text=CURRENCY_HELP_TEXT)
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                help_text=CURRENCY_HELP_TEXT)
    date = serializers.DateTimeField(required=True)

    def validate(self, attrs):
        if False and comp_date > datetime.today() + timedelta(days=365):
            raise serializers.ValidationError("Date beyond calendar scope")
        fxpair = FxPair.get_pair_from_currency(attrs.get('sell_currency'), attrs.get('buy_currency'))
        attrs['market_name'] = fxpair.market
        return attrs


class SingleDayTenorSerializer(SingleDaySerializer):
    tenor = serializers.CharField(default="SPOT")
    date = serializers.DateTimeField(required=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        return attrs


class MarketNameSerializer(serializers.Serializer):
    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                 help_text=CURRENCY_HELP_TEXT)
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                help_text=CURRENCY_HELP_TEXT)

    def validate(self, attrs):
        fxpair = FxPair.get_pair_from_currency(attrs.get('sell_currency'), attrs.get('buy_currency'))
        attrs['market_name'] = fxpair.market
        return attrs


class MultiDaySerializer(serializers.Serializer):
    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                 help_text=CURRENCY_HELP_TEXT)
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                help_text=CURRENCY_HELP_TEXT)
    dates = serializers.ListField(
        child=serializers.DateField(), required=True
    )
    rule = serializers.ChoiceField(choices=Ticket.DateConvs.choices, default=Ticket.DateConvs.MODF)


class DatesResponseSerializer(serializers.ListSerializer):
    child = serializers.DateField()

# ============

class NonSettlementDaysView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        request=DateRangeSerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = DateRangeSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse('Invalid request', status=status.HTTP_400_BAD_REQUEST, errors=serializer.errors)

        data = serializer.validated_data
        start_date = data['start_date'] or date.today()
        end_date = data['end_date'] or date.today() + timedelta(days=365)
        dates = get_non_settlement_days(data['market_name'], start_date, end_date)
        return Response(dates, status=status.HTTP_200_OK)


class SettlementDaysView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        request=DateRangeSerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = DateRangeSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse('Invalid request', status=status.HTTP_400_BAD_REQUEST, errors=serializer.errors)

        data = serializer.validated_data
        start_date = data['start_date'] or date.today()
        end_date = data['end_date'] or date.today() + timedelta(days=365)
        dates = get_settlement_days(data['market_name'], start_date, end_date)
        return Response(dates, status=status.HTTP_200_OK)


class IsValidSettlementDayView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        request=SingleDaySerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = SingleDaySerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse('Invalid request', status=status.HTTP_400_BAD_REQUEST, errors=serializer.errors)

        data = serializer.validated_data
        resp = is_valid_settlement_day(data['market_name'], data['date'])
        return Response(resp, status=status.HTTP_200_OK)


class NextValidSettlementDayView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        request=SingleDaySerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = SingleDaySerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse('Invalid request', status=status.HTTP_400_BAD_REQUEST, errors=serializer.errors)

        data = serializer.validated_data
        resp = next_valid_settlement_day(data['market_name'], data['date'])
        return Response(resp, status=status.HTTP_200_OK)


class PrevValidSettlementDayView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        request=SingleDaySerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = SingleDaySerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse('Invalid request', status=status.HTTP_400_BAD_REQUEST, errors=serializer.errors)

        data = serializer.validated_data
        resp = prev_valid_settlement_day(data['market_name'], data['date'])
        return Response(resp, status=status.HTTP_200_OK)


class NextMktDayView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        request=SingleDaySerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = SingleDaySerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse('Invalid request', status=status.HTTP_400_BAD_REQUEST, errors=serializer.errors)

        data = serializer.validated_data
        resp = get_next_mkt_session(data['market_name'], data['date'])
        return Response(resp, status=status.HTTP_200_OK)


class CurrentMktDayView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        request=SingleDaySerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = SingleDaySerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse('Invalid request', status=status.HTTP_400_BAD_REQUEST, errors=serializer.errors)

        data = serializer.validated_data
        resp = get_current_mkt_session(data['market_name'], data['date'])
        return Response(resp, status=status.HTTP_200_OK)


class FxSettlementInfoView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        request=SingleDayTenorSerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = SingleDayTenorSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse('Invalid request', status=status.HTTP_400_BAD_REQUEST, errors=serializer.errors)

        data = serializer.validated_data
        resp = get_fx_settlement_info(data['market_name'], data['date'], tenor=data['tenor'])
        return Response(resp, status=status.HTTP_200_OK)


class FxSpotValueDateView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        request=SingleDateTimeSerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = SingleDateTimeSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse('Invalid request', status=status.HTTP_400_BAD_REQUEST, errors=serializer.errors)

        data = serializer.validated_data
        resp = get_fx_spot_info(data['market_name'], dt=data['date'])
        return Response(resp, status=status.HTTP_200_OK)


class BestExecutionView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    cache = {}

    @extend_schema(
        summary="Best Execution",
        description="Endpoint for market execution recommendation.",
        request=MarketNameSerializer,
        responses={
            400: EXTERNAL_PANGEA_400,
            401: EXTERNAL_PANGEA_401,
            403: EXTERNAL_PANGEA_403,
            404: EXTERNAL_PANGEA_404,
            500: EXTERNAL_PANGEA_500,
            status.HTTP_200_OK: BestExecutionSerializer,
        },
        tags=['Execution Management'],
        examples=[
            OpenApiExample(
                name='Invalid Request',
                # description='some description'
                value={
                    'error_message': 'Invalid request',
                },
                response_only=True,
                status_codes=['400'],
            ),
            OpenApiExample(
                name='Execution Recommended',
                # description='some description'
                value={
                    'market': 'USDMXN',
                    'recommend': True,
                    'session': 'New_York',
                    'check_back': None,
                    'execute_before': datetime.utcnow() + timedelta(minutes=5),
                    'unsupported': False,
                },
                response_only=True,
                status_codes=['200'],
            ),
            OpenApiExample(
                name='Execution Not Recommended',
                # description='some description'
                value={
                    'market': 'USDMXN',
                    'recommend': False,
                    'session': 'Weekend',
                    'check_back': datetime.utcnow() + timedelta(hours=24),
                    'execute_before': None,
                    'unsupported': False,
                },
                response_only=True,
                status_codes=['200'],
            ),
            OpenApiExample(
                name='Execution Open, Not Recommended',
                # description='some description'
                value={
                    'market': 'USDMXN',
                    'recommend': False,
                    'session': 'FridayLate',
                    'check_back': datetime.utcnow() + timedelta(hours=24),
                    'execute_before': datetime.utcnow() + timedelta(minutes=5),
                    'unsupported': False,
                },
                response_only=True,
                status_codes=['200'],
            ),
        ]
    )
    def post(self, request, *args, **kwargs):

        self.cache.clear()

        if hasattr(request._request, 'data') and isinstance(request._request.data, list):
            ret = []
            for rdata in request._request.data:
                response = self.do_request(rdata, request._request.user)
                ret.append(response)
            self.cache.clear()
            return MultiResponse(ret)
        elif hasattr(request._request, 'data') and isinstance(request._request.data, dict) \
            and request._request.data != {}:
            return self.do_request(request._request.data, request._request.user)
        elif isinstance(request.data, list):
            ret = []
            for rdata in request.data:
                response = self.do_request(rdata, request.user)
                ret.append(response)
            self.cache.clear()
            return MultiResponse(ret)
        else:
            return self.do_request(request.data, request.user)

        return self.do_request(request.data, request.user)

    def do_request(self, request_data, request_user):
        serializer = MarketNameSerializer(data=request_data)
        if not serializer.is_valid():
            return ErrorResponse('Invalid request', status=status.HTTP_400_BAD_REQUEST, errors=serializer.errors)
        data = serializer.validated_data
        mkt_nm = data['market_name']
        if mkt_nm in self.cache:
            return self.cache[mkt_nm]
        status = get_best_execution_status(data['market_name'])
        resp = BestExecutionSerializer(status)
        ret = Response(resp.data, status=status.HTTP_200_OK)
        self.cache[mkt_nm] = ret
        return ret


# =====

class ValueDateValidator(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        request=MultiDaySerializer,
        responses=DatesResponseSerializer
    )
    def post(self, request, *args, **kwargs):
        serializer = MultiDaySerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse('Invalid request', status=status.HTTP_400_BAD_REQUEST, errors=serializer.errors)
        data = serializer.validated_data
        dates = CalendarService().infer_value_dates(data['buy_currency'], data['sell_currency'], data['dates'],
                                                    rule=data['rule'])
        return Response(dates, status=status.HTTP_200_OK)


if __name__ == "__main__":
    mkt = 'EURUSD'
    start_date = date.today()
    end_date = start_date + timedelta(days=30)

    nsd = get_non_settlement_days(mkt, start_date, end_date)
    sd = get_settlement_days(mkt, start_date, end_date)
    valid = is_valid_settlement_day(mkt, end_date)
