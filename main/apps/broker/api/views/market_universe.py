from django.db.models import Q, F
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from main.apps.broker.models.company_perm import BrokerCompanyInstrument

from main.apps.core.constants import CURRENCY_HELP_TEXT
from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.corpay.models.beneficiary import Beneficiary
from main.apps.currency.models import Currency
from main.apps.oems.api.utils.response import *
from main.apps.oems.models import CnyExecution


# =======

class BuySellSerializer(serializers.Serializer):
    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                 allow_null=True, default=None, help_text=CURRENCY_HELP_TEXT)
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                allow_null=True, default=None, help_text=CURRENCY_HELP_TEXT)


class CurrencyResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    symbol = serializers.CharField()
    symbol_location = serializers.CharField()
    mnemonic = serializers.CharField()
    name = serializers.CharField()
    unit = serializers.IntegerField()
    numeric_code = serializers.CharField()
    country = serializers.CharField()
    image_thumbnail = serializers.CharField()
    image_banner = serializers.CharField()
    category = serializers.CharField()
    currency = serializers.CharField()
    active = serializers.BooleanField()
    available = serializers.BooleanField()


class CurrencyResponseListSerializer(serializers.ListSerializer):
    child = CurrencyResponseSerializer()


class ResponseSerializer(serializers.Serializer):
    buy_currency = CurrencyResponseListSerializer()
    sell_currency = CurrencyResponseListSerializer()


# =======

MAJORS = ('USD', 'EUR', 'GBP', 'CAD', 'MXN')
ACTIVE_CCYS = [
    'XAG',
    'XAU',
    'BTC',
    'ETH',
    'EUR',
    'GBP',
    'AUD',
    'NZD',
    'USD',
    'CAD',
    'CHF',
    'NOK',
    'SEK',
    'BRL',
    'MXN',
    'HKD',
    'TRY',
    'ZAR',
    'PLN',
    'HUF',
    'CZK',
    'SGD',
    'CNY',
    'CNH',
    'KRW',
    'INR',
    'TWD',
    'THB',
    'MYR',
    'ILS',
    'IDR',
    'CLP',
    'COP',
    'PEN',
    'PHP',
    'JPY',
    'NGN',
    'KES',
    'UGX',
    'PHP',
    'ZMW',
    'TZS',
]


def get_ccy_sort_index(x, preferences):
    try:
        return preferences.index(x)
    except ValueError:
        return 1000


class CompanyMarketUniverse(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        request=BuySellSerializer,
        responses={
            400: EXTERNAL_PANGEA_400,
            401: EXTERNAL_PANGEA_401,
            403: EXTERNAL_PANGEA_403,
            404: EXTERNAL_PANGEA_404,
            500: EXTERNAL_PANGEA_500,
            status.HTTP_200_OK: ResponseSerializer,
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = BuySellSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse('Invalid request', status=status.HTTP_400_BAD_REQUEST, errors=serializer.errors)
        data = serializer.validated_data
        # filter based on buy/sell currencies

        buy_ccy = data['buy_currency'].mnemonic if data['buy_currency'] else None
        sell_ccy = data['sell_currency'].mnemonic if data['sell_currency'] else None

        response = {
            'buy_currency': [],
            'sell_currency': [],
        }

        # unique_values = Beneficiary.objects.filter(company=request.user.company.id).values_list('currency', flat=True).distinct()
        # bene_currencies = {Currency.objects.get(pk=ccy_id).mnemonic for ccy_id in unique_values}

        # permissioned currencies by user
        base_ccy = BrokerCompanyInstrument.objects\
            .filter(active=True, company=request.user.company).values_list('broker_instrument__base_ccy',
                                                                                flat=True).distinct()
        cntr_ccy = BrokerCompanyInstrument.objects\
            .filter(active=True, company=request.user.company).values_list('broker_instrument__counter_ccy',
                                                                                flat=True).distinct()
        permission_currencies = set(base_ccy) | set(cntr_ccy)

        """
        for bi in BrokerUserInstrument.objects.filter(user=request.user):
            permission_currencies.add( bi.base_ccy )
            permission_currencies.add( bi.counter_ccy )
        """

        unique_values = Beneficiary.objects.filter(company=request.user.company.id).values_list('currency__mnemonic',
                                                                                                flat=True).distinct()
        bene_currencies = set(unique_values)

        ccy_preferences = []  # list(bene_currencies) if bene_currencies else []
        # ccy_preferences.sort(key=lambda x: x!='USD')
        # print('currency prefs:', ccy_preferences)
        active_ccys = self._get_active_ccys()
        active_base_ccys = self._get_active_ccys(side='base')
        active_quote_ccys = self._get_active_ccys(side='quote')
        universe = list(set(active_ccys + list(bene_currencies))) if bene_currencies else active_ccys

        currencies = Currency.objects.filter(mnemonic__in=universe)

        usd = None

        for ccy in currencies:
            if ccy.mnemonic not in active_quote_ccys:
                continue
            tmp = vars(ccy).copy()
            try:
                del tmp['_state']
            except:
                pass
            # if ccy.mnemonic == sell_ccy and ccy.mnemonic != ('USD','EUR'): continue
            tmp['currency'] = ccy.mnemonic
            tmp['active'] = True
            tmp['available'] = (ccy.mnemonic in permission_currencies)
            # tmp['amount_rounding'] = (0 if ccy.mnemonic in self.WHOLE_CCYS else 2)
            response['buy_currency'].append(tmp)
            if ccy.mnemonic == 'USD' and usd is None:
                usd = tmp.copy()
                usd['id'] = 0

        for ccy in currencies:
            if ccy.mnemonic not in active_base_ccys:
                continue
            tmp = vars(ccy).copy()
            try:
                del tmp['_state']
            except:
                pass
            tmp['currency'] = ccy.mnemonic
            tmp['active'] = True
            tmp['available'] = (ccy.mnemonic in permission_currencies)
            # tmp['amount_rounding'] = (0 if ccy.mnemonic in self.WHOLE_CCYS else 2)
            response['sell_currency'].append(tmp)
            if ccy.mnemonic == 'USD' and usd is None:
                usd = tmp.copy()
                usd['id'] = 0

        # =============

        if response['buy_currency']:
            # response['buy_currency'].sort(key=lambda x: (not x['currency'] == buy_ccy, not x['active'], get_ccy_sort_index(x['currency'],ccy_preferences), x['currency']))
            response['buy_currency'].sort(
                key=lambda x: (not x['available'], (x['currency'] not in ccy_preferences), x['currency']))

        if response['sell_currency']:
            # response['sell_currency'].sort(key=lambda x: (not x['currency'] == sell_ccy, not x['active'], get_ccy_sort_index(x['currency'],ccy_preferences), x['currency']))
            response['sell_currency'].sort(
                key=lambda x: (not x['available'], (x['currency'] not in ccy_preferences), x['currency']))

        if usd:
            response['buy_currency'] = [currency for currency in response['buy_currency'] if
                                        currency['mnemonic'] != 'USD']
            response['buy_currency'].insert(0, usd)
            response['sell_currency'] = [currency for currency in response['sell_currency'] if
                                         currency['mnemonic'] != 'USD']
            response['sell_currency'].insert(0, usd)

        return Response(response, status=status.HTTP_200_OK)

    def _get_active_ccys(self, side=None):
        company = self.request.user.company
        executions = CnyExecution.objects.filter(company=company, active=True).select_related(
            'fxpair__quote_currency',
            'fxpair__base_currency'
        )

        if side == 'base':
            currencies = executions.values_list('fxpair__base_currency__mnemonic', flat=True)
        elif side == 'quote':
            currencies = executions.values_list('fxpair__quote_currency__mnemonic', flat=True)
        else:
            # When side is None, we need to get both base and quote currencies
            currencies = executions.annotate(
                base_mnemonic=F('fxpair__base_currency__mnemonic'),
                quote_mnemonic=F('fxpair__quote_currency__mnemonic')
            ).values_list('base_mnemonic', 'quote_mnemonic')
            # Flatten the list of tuples into a single list
            currencies = [ccy for pair in currencies for ccy in pair]

        return list(set(currencies))
