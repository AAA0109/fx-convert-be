import traceback
import pandas as pd
from datetime import datetime, date, timedelta
from math import sqrt

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView

from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.core.utils.slack import send_exception_to_slack
from main.apps.currency.models.fxpair import FxPair
from main.apps.marketdata.api.serializers.initial import (
    InitialMarketStateRequestSerializer,
    InitialMarketStateResponseSerializer,
    RecentRateResponseSerializer,
    InitialRateRequestSerializer,
    HistoricalRateRequestSerializer,
    MarketVolatilitySerializer,
    RecentVolResponseSerialier,
    HistoricalRateResponseSerializer,
)
from main.apps.marketdata.models import FxSpotVol
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
from main.apps.marketdata.services.initial_marketdata import InitialMarketDataProvider, get_ccy_legs, \
    ccy_triangulate_rate
from main.apps.marketdata.services.moving_average import HistoricalSpotDataProvider, MovingAverageProvider
from main.apps.oems.api.utils.response import *


class InitialMarketDataApiView(APIView):
    permission_classes = [IsAuthenticated]


class InitialMarketStateApiView(InitialMarketDataApiView):
    @extend_schema(
        request=InitialMarketStateRequestSerializer,
        responses={
            status.HTTP_200_OK: InitialMarketStateResponseSerializer,
            207: EXTERNAL_PANGEA_207,
            400: EXTERNAL_PANGEA_400,
            401: EXTERNAL_PANGEA_401,
            403: EXTERNAL_PANGEA_403,
            404: EXTERNAL_PANGEA_404,
            500: EXTERNAL_PANGEA_500,
        }
    )
    def post(self, request: Request, *args, **kwargs):

        if hasattr(request._request, 'data') and isinstance(request._request.data, list):
            ret = []
            for rdata in request._request.data:
                try:
                    response = self.do_request(rdata, request._request.user)
                except Exception as e:
                    traceback.print_exc()
                    send_exception_to_slack(e, key='oems-rfq')
                    response = INTERNAL_ERROR_RESPONSE
                ret.append(response)
            return MultiResponse(ret)
        elif hasattr(request._request, 'data') and isinstance(request._request.data, dict) \
            and request._request.data != {}:
            try:
                return self.do_request(request._request.data, request._request.user)
            except Exception as e:
                traceback.print_exc()
                return INTERNAL_ERROR_RESPONSE
        elif isinstance(request.data, list):
            ret = []
            for rdata in request.data:
                try:
                    response = self.do_request(rdata, request.user)
                except Exception as e:
                    traceback.print_exc()
                    response = INTERNAL_ERROR_RESPONSE
                ret.append(response)
            return MultiResponse(ret)
        else:
            try:
                return self.do_request(request.data, request.user)
            except Exception as e:
                traceback.print_exc()
                return INTERNAL_ERROR_RESPONSE

    def do_request(self, request_data, request_user):

        # TODO: we need to get the company from request.user.company
        # then parse the max tenor across all brokers
        # this will determine which broker we can use
        # if broker is provided... set max tenor that way
        try:
            serializer = InitialMarketStateRequestSerializer(data=request_data)
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            try:
                emsg = e.detail['non_field_errors'][0]
            except:
                emsg = 'validation failed'
            return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)

        try:
            sell_ccy = serializer.validated_data.get('sell_currency')
            buy_ccy = serializer.validated_data.get('buy_currency')
            value_date = serializer.validated_data.get('value_date')
            provider = InitialMarketDataProvider(
                sell_currency=sell_ccy,
                buy_currency=buy_ccy,
                tenor=value_date,
                company=request_user.company
            )
            initial_state = provider.get_initial_market_state()
            resp_data = InitialMarketStateResponseSerializer(initial_state)
            return Response(resp_data.data, status=status.HTTP_200_OK)
        except Exception as e:
            traceback.print_exc()
            return ErrorResponse('internal error', status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RecentRateApiView(InitialMarketDataApiView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        request=InitialRateRequestSerializer,
        summary="Indicative Rate",
        description="Endpoint for indicative rate.",
        tags=['Rates'],
        responses={
            200: OpenApiResponse(response=RecentRateResponseSerializer,
                                 description='Recent Rate'),
            400: EXTERNAL_PANGEA_400,
            401: EXTERNAL_PANGEA_401,
            403: EXTERNAL_PANGEA_403,
            404: EXTERNAL_PANGEA_404,
            500: EXTERNAL_PANGEA_500,
        },
    )
    def post(self, request: Request, *args, **kwargs):
        try:
            serializer = InitialRateRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            provider = InitialMarketDataProvider(
                sell_currency=serializer.validated_data.get('sell_currency'),
                buy_currency=serializer.validated_data.get('buy_currency'),
                tenor=serializer.validated_data.get('value_date')
            )
            initial_state = provider.get_recent_data()
            if initial_state.get('spot_rate') is None:
                return ErrorResponse('No rate found', status=status.HTTP_404_NOT_FOUND, code=404, )
            resp_data = RecentRateResponseSerializer(initial_state)
            return Response(resp_data.data, status=status.HTTP_200_OK)
        except serializers.ValidationError as e:
            try:
                emsg = e.detail['non_field_errors'][0]
            except:
                emsg = 'validation failed'
            return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)
        except Exception as e:
            traceback.print_exc()
            return Response({'msg': 'internal error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==========

class RecentVolApiView(InitialMarketDataApiView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        request=MarketVolatilitySerializer,
        summary="Market Risk",
        description="Endpoint for current market risk.",
        tags=['Rates'],
        responses={
            400: EXTERNAL_PANGEA_400,
            401: EXTERNAL_PANGEA_401,
            403: EXTERNAL_PANGEA_403,
            404: EXTERNAL_PANGEA_404,
            500: EXTERNAL_PANGEA_500,
            200: OpenApiResponse(response=RecentVolResponseSerialier,
                                 description='Recent Volatility'),
        },
    )
    def post(self, request: Request, *args, **kwargs):
        try:
            serializer = MarketVolatilitySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # get historical rates per serializer.validated_data
            fxpair = serializer.validated_data.get('fxpair')

            opt = FxSpotVol.get_spot_vol(fxpair=fxpair, estimator=3, date=datetime.utcnow())

            # TODO: if triangulate, use justin's formulas

            if not opt:
                emsg = f"no vol data for {fxpair}"
                return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST)

            # days = 7
            vd = serializer.validated_data.get('value_date')
            v_at_t = None  # daily vol
            if vd:
                try:
                    days = (vd - date.today()).days - 2
                    if days > 1:
                        v_at_t = round(opt[0] * 100 / sqrt(365 / days), 2)
                    else:
                        v_at_t = round(opt[0] * 100 / sqrt(260.0), 2)
                except:
                    pass

            # add vol days?
            data = {'value_date': vd, 'annual_volatility': round(opt[0] * 100, 2),
                    'monthly_volatility': round(opt[0] * 100 / sqrt(12)),
                    'daily_volatility': round(opt[0] * 100 / sqrt(260.0), 2), "volatility_at_t": v_at_t,
                    "unit": "percent"}
            resp_data = RecentVolResponseSerialier(data)
            return Response(resp_data.data, status=status.HTTP_200_OK)
        except serializers.ValidationError as e:
            try:
                emsg = e.detail['non_field_errors'][0]
            except:
                emsg = 'validation failed'
            return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)
        except Exception as e:
            traceback.print_exc()
            return Response({'msg': 'internal error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==========

class HistoricalRateApiView(InitialMarketDataApiView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        request=HistoricalRateRequestSerializer,
        summary="Historical Rates",
        description="Endpoint for spot daily historical rates.",
        tags=['Rates'],
        responses={
            200: OpenApiResponse(response=HistoricalRateResponseSerializer,
                                 description='Historical OHLC'),
            400: EXTERNAL_PANGEA_400,
            401: EXTERNAL_PANGEA_401,
            403: EXTERNAL_PANGEA_403,
            404: EXTERNAL_PANGEA_404,
            500: EXTERNAL_PANGEA_500,
        },
    )
    def post(self, request: Request, *args, **kwargs):
        try:
            # TODO: validate company credentials
            serializer = HistoricalRateRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # get historical rates per serializer.validated_data
            fxpair = serializer.validated_data.get('fxpair')
            invert = serializer.validated_data.get('invert')
            triangulate = ('USD' not in fxpair.market)
            vd = serializer.validated_data.get('value_date')
            if vd != "SPOT":
                raise serializers.ValidationError('Unsupported tenor')
            start_date = serializer.validated_data.get('start_date')
            end_date = serializer.validated_data.get('end_date')

            ma_svc = MovingAverageProvider(pair=fxpair, invert=invert, triangulate=triangulate)
            ma_svc.set_moving_avg_window(start_date=start_date, end_date=end_date)

            end_time = end_date
            start_time = start_date - timedelta(days=2 * ma_svc.n_days)

            spot_data_provider = HistoricalSpotDataProvider(pair=fxpair, invert=invert, triangulate=triangulate)
            spot_data = spot_data_provider.get_historical_spot_data(start_date=start_time, end_date=end_time)
            ma_data = ma_svc.calculate_moving_average(start_date=start_date, end_date=end_date, spot_data=spot_data)

            df = pd.DataFrame(
                data=spot_data,
                columns=['date', 'rate']
            )
            df = df.loc[(df['date'] >= start_date)]
            df.set_index('date', inplace=True)
            df.fillna(df.mean(), inplace=True)

            # Get average rate data
            # daily if moving average window = 20
            # weekly if moving average window = 50
            # monthly if moving average window = 200
            if ma_svc.n_days == 20:
                df = df.resample('D').agg({
                    'rate': 'mean',
                })
            elif ma_svc.n_days == 50:
                df = df.resample('W-FRI').agg({
                    'rate': 'mean',
                })
            elif ma_svc.n_days == 200:
                df = df.resample('M').agg({
                    'rate': 'mean',
                })

            df.replace({float('nan'): None}, inplace=True)

            resp_data = []
            for index, row in df.iterrows():
                if index.date() >= start_date.date():
                    if row[0] is None:
                        continue

                    moving_avg = ma_svc.get_moving_avg_data_by_date(
                            ma_data=ma_data,
                            key=index.date(),
                            threshold_date=end_date.date())

                    if moving_avg is None:
                        continue

                    resp_data.append({
                        'date': index.date(),
                        'rate': row[0],
                        'rate_ma': moving_avg['rate_ma']
                    })

            return Response(resp_data, status=status.HTTP_200_OK)
        except serializers.ValidationError as e:
            try:
                emsg = e.detail['non_field_errors'][0]
            except:
                emsg = 'validation failed'
            return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)
        except Exception as e:
            traceback.print_exc()
            return ErrorResponse('internal error', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
