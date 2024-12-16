import logging

from typing import OrderedDict

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from main.apps.corpay.api.serializers.spot.balance import CalculateBalanceRequestSerializer, \
    CalculateBalanceResponseSerializer

from main.apps.corpay.api.serializers.spot.book_deal import BookDealRequestSerializer, BookDealResponseSerializer
from main.apps.corpay.api.serializers.spot.book_instruct_deal import BookInstructDealRequestSerializer, \
    SaveInstructRequestSerializer
from main.apps.corpay.api.serializers.spot.instruct_deal import InstructDealRequestSerializer, \
    InstructDealResponseSerializer
from main.apps.corpay.api.serializers.spot.instruct_request import SaveInstructRequestResponseSerializer
from main.apps.corpay.api.serializers.spot.purpose_of_payment import PurposeOfPaymentRequestSerializer, \
    PurposeOfPaymentResponseSerializer
from main.apps.corpay.api.serializers.spot.rate import SpotRateRequestSerializer, SpotRateResponseSerializer
from main.apps.corpay.api.views.base import CorPayBaseView
from main.apps.settlement.models import Beneficiary
from main.apps.corpay.models.fx_balance import FXBalance
from main.apps.corpay.services.api.dataclasses.spot import PurposeOfPaymentParams, InstructDealOrder, \
    InstructDealPayment, InstructDealSettlement, InstructDealBody, SpotRateBody
from main.apps.corpay.services.cost import CorpayCostService

from main.apps.corpay.services.fxbalance.balance import CorPayFXBalanceDraftService
from main.apps.corpay.services.instruct_request import InstructRequestService
from main.apps.currency.models import Currency
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider

logger = logging.getLogger(__name__)


class CreateSpotRateView(CorPayBaseView):

    @extend_schema(
        request=SpotRateRequestSerializer,
        responses={
            status.HTTP_200_OK: SpotRateResponseSerializer
        }
    )
    def post(self, request):
        self.corpay_service.init_company(request.user.company)
        serializer = SpotRateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = self.corpay_service.get_spot_rate(data=serializer.validated_data)
        self._add_domestic_amount_to_response(response, request.user.company.currency)
        response['cost_in_bps'] = self.__calculate_transparent_fee(request=request,
                                                                   validated_data=serializer.validated_data)
        response_serializer = SpotRateResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)

    def _convert_currency(self, amount: float, from_currency: str, to_currency: str):
        if from_currency == to_currency:
            return amount

        data = SpotRateBody(
            paymentCurrency=to_currency,
            settlementCurrency=from_currency,
            amount=amount,
            lockSide='settlement'
        )
        _response = self.corpay_service.get_spot_rate(data=data)
        return _response['payment']['amount']

    def _add_domestic_amount_to_response(self, response: OrderedDict, company_currency: Currency):
        payment = response['payment']
        payment['amount_domestic'] = self._convert_currency(
            payment['amount'],
            payment['currency'],
            company_currency.mnemonic
        )

        settlement = response['settlement']
        settlement['amount_domestic'] = self._convert_currency(
            settlement['amount'],
            settlement['currency'],
            company_currency.mnemonic
        )

        response['payment'] = payment
        response['settlement'] = settlement
        return response

    def __calculate_transparent_fee(self, request, validated_data: SpotRateBody) -> int:
        company = request.user.company
        currency = Currency.get_currency(
            currency=validated_data.paymentCurrency) if validated_data.lockSide == "payment" else Currency.get_currency(
            currency=validated_data.settlementCurrency)
        amount = self._convert_currency(amount=validated_data.amount, from_currency=currency.mnemonic,
                                        to_currency=request.user.company.currency.mnemonic)
        cost_service = CorpayCostService(company=company)
        transaction_cost = cost_service.get_cost(amount_in_usd=amount, currency=currency)

        return transaction_cost.cost_in_bps if transaction_cost else None


class CreateBookSpotDealView(CorPayBaseView):
    @extend_schema(
        request=BookDealRequestSerializer,
        responses={
            status.HTTP_200_OK: BookDealResponseSerializer
        }
    )
    def post(self, request):
        self.corpay_service.init_company(request.user.company)
        serializer = BookDealRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = self.corpay_service.book_spot_deal(quote_id=serializer.validated_data.get('quote_id'))
        response_serializer = BookDealResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)


class CreateInstructSpotDealView(CorPayBaseView):
    @extend_schema(
        request=InstructDealRequestSerializer,
        responses={
            status.HTTP_200_OK: InstructDealResponseSerializer
        }
    )
    def post(self, request):
        self.corpay_service.init_company(request.user.company)
        serializer = InstructDealRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        orders = []
        for order in serializer.validated_data.get('orders'):
            orders.append(
                InstructDealOrder(
                    orderId=order['order_id'],
                    amount=order['amount']
                )
            )
        payments = []
        for payment in serializer.validated_data.get('payments'):
            payments.append(
                InstructDealPayment(
                    amount=payment['amount'],
                    beneficiaryId=payment['beneficiary_id'],
                    deliveryMethod=payment['delivery_method'],
                    currency=payment['currency'],
                    purposeOfPayment=payment['purpose_of_payment']
                )
            )
        settlements = []
        for settlement in serializer.validated_data.get('settlements'):
            settlements.append(
                InstructDealSettlement(
                    accountId=settlement['account_id'],
                    deliveryMethod=settlement['delivery_method'],
                    currency=settlement['currency'],
                    purpose=settlement['purpose']
                )
            )
        data = InstructDealBody(
            orders=orders,
            payments=payments,
            settlements=settlements
        )
        response = self.corpay_service.instruct_spot_deal(data=data)
        response_serializer = InstructDealResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)


class CreateBookAndInstructSpotDealView(CorPayBaseView):
    @extend_schema(
        request=BookInstructDealRequestSerializer,
        responses={
            status.HTTP_200_OK: InstructDealResponseSerializer
        }
    )
    def post(self, request):
        self.corpay_service.init_company(request.user.company)
        serializer = BookInstructDealRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book_request = serializer.validated_data.get('book_request')
        instruct_request = serializer.validated_data.get('instruct_request')
        book_deal_response = self.corpay_service.book_spot_deal(quote_id=book_request.get('quote_id'))

        orders = []
        for order in instruct_request.get('orders'):
            orders.append(
                InstructDealOrder(
                    orderId=book_deal_response['orderNumber'],
                    amount=order['amount']
                )
            )
        payments = []
        for payment in instruct_request.get('payments'):
            payments.append(
                InstructDealPayment(
                    amount=payment['amount'],
                    beneficiaryId=payment['beneficiary_id'],
                    deliveryMethod=payment['delivery_method'],
                    currency=payment['currency'],
                    purposeOfPayment=payment['purpose_of_payment']
                )
            )
        settlements = []
        for settlement in instruct_request.get('settlements'):
            settlements.append(
                InstructDealSettlement(
                    accountId=settlement['account_id'],
                    deliveryMethod=settlement['delivery_method'],
                    currency=settlement['currency'],
                    purpose=settlement['purpose']
                )
            )
        data = InstructDealBody(
            orders=orders,
            payments=payments,
            settlements=settlements
        )
        try:
            response = self.corpay_service.instruct_spot_deal(data=data)
            CorPayFXBalanceDraftService().create(request.user.company, response)

        except Exception as e:
            logger.debug(f"Error on instruct_spot_deal call - {request.user.company.name} - "
                        f"ID: {request.user.company.pk}: {e}")
            raise e

        response_serializer = InstructDealResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)


class ListPurposeOfPaymentView(CorPayBaseView):
    @extend_schema(
        parameters=[PurposeOfPaymentRequestSerializer],
        responses={
            status.HTTP_200_OK: PurposeOfPaymentResponseSerializer
        }
    )
    def get(self, request):
        self.corpay_service.init_company(request.user.company)
        serializer = PurposeOfPaymentRequestSerializer(data=request.GET)
        serializer.is_valid(raise_exception=True)
        params = PurposeOfPaymentParams(
            countryISO=serializer.validated_data.get('country'),
            curr=serializer.validated_data.get('currency'),
            method=serializer.validated_data.get('method')
        )

        purposes = [
            {'id': choice.value, 'text': choice.label, 'searchText': choice.label.lower()} for choice in Beneficiary.Purpose
        ]
        response =  {"items": purposes}

        response_serializer = PurposeOfPaymentResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)


class SaveInstructDealRequestView(CorPayBaseView):
    @extend_schema(
        request=SaveInstructRequestSerializer,
        responses={
            status.HTTP_200_OK: SaveInstructRequestResponseSerializer
        }
    )
    def post(self, request):
        serializer = SaveInstructRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quote_id = serializer.validated_data.get('quote_id')
        instruct_request = serializer.validated_data.get('instruct_request')

        try:
            instruct_request_service = InstructRequestService(instruct_request=instruct_request, quote_id=quote_id)
            order_instruct_request = instruct_request_service.save_instruct_request()
            instruct_request_response = SaveInstructRequestResponseSerializer(order_instruct_request)
            return Response(instruct_request_response.data, status.HTTP_200_OK)
        except Exception as e:
            return Response({"msg": str(e)}, status.HTTP_400_BAD_REQUEST)


class CalculateBalanceView(CorPayBaseView):

    def convert_amount(self, amount: float, balance_data: FXBalance, currency: Currency) -> float:
        spot_cache = FxSpotProvider().get_spot_cache(time=balance_data.modified)
        converted_amount = spot_cache.convert_value(amount, currency, balance_data.currency)
        return converted_amount

    def return_null_value(self) -> Response:
        return Response({'from_value': None, 'to_value': None}, status.HTTP_200_OK)

    @extend_schema(
        request=CalculateBalanceRequestSerializer,
        responses={
            status.HTTP_200_OK: CalculateBalanceResponseSerializer
        }
    )
    def post(self, request):
        serializer = CalculateBalanceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        currency_id_or_mnemonic = serializer.validated_data.get('currency')
        from_balance = serializer.validated_data.get('from_balance')
        to_balance = serializer.validated_data.get('to_balance')
        amount = serializer.validated_data.get('amount')

        currency = Currency.get_currency(currency=currency_id_or_mnemonic)

        if not currency:
            return Response({"error": f"Can't find currency with menmonic or id {currency_id_or_mnemonic}"},
                            status.HTTP_400_BAD_REQUEST)

        if from_balance['type'] != "fx_balance" or to_balance['type'] != "fx_balance":
            return self.return_null_value()

        try:
            from_balance_data = FXBalance.objects.filter(account_number=from_balance['id']).latest('created')
            to_balance_data = FXBalance.objects.filter(account_number=to_balance['id']).latest('created')
        except Exception as e:
            logger.error(str(e))
            return self.return_null_value()

        if from_balance_data.account_number == to_balance_data.account_number:
            return Response({"error": f"Can't transfer to the same account number {to_balance_data.account_number}"},
                            status.HTTP_400_BAD_REQUEST)

        converted_amount_from = self.convert_amount(amount, balance_data=from_balance_data, currency=currency)
        converted_amount_to = self.convert_amount(amount, balance_data=to_balance_data, currency=currency)

        from_value = from_balance_data.balance - converted_amount_from
        to_value = to_balance_data.balance + converted_amount_to

        return Response({'from_value': from_value, 'to_value': to_value}, status.HTTP_200_OK)
