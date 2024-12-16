from typing import OrderedDict

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from main.apps.account.models import Company
from main.apps.broker.models import CurrencyFee
from main.apps.corpay.api.serializers.mass_payments import QuotePaymentsResponseSerializer, \
    BookPaymentsResponseSerializer
from main.apps.corpay.api.serializers.payment import QuotePaymentSerializer, BookPaymentRequestSerializer, \
    QuotePaymentResponseSerializer
from main.apps.corpay.api.serializers.spot.rate import SpotRateRequestSerializer
from main.apps.corpay.api.views.base import CorPayBaseView
from main.apps.corpay.models import CorpaySettings, Locksides
from main.apps.corpay.services.api.dataclasses.mass_payment import QuotePayment, QuotePaymentsBody, BookPaymentsParams, \
    BookPaymentsBody
from main.apps.corpay.services.api.dataclasses.spot import SpotRateBody


class CorPayQuotePaymentView(CorPayBaseView):
    @extend_schema(
        request=QuotePaymentSerializer,
        responses={
            status.HTTP_200_OK: QuotePaymentResponseSerializer
        }
    )
    def post(self, request):
        self.corpay_service.init_company(request.user.company)
        serializer = QuotePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # TODO: Use ICE rate here
        rate_request_serializer = SpotRateRequestSerializer(data={
            'payment_currency': serializer.validated_data.paymentCurrency,
            'settlement_currency': serializer.validated_data.settlementCurrency,
            'amount': serializer.validated_data.amount,
            'lock_side': serializer.validated_data.lockside
        })
        rate_request_serializer.is_valid(raise_exception=True)
        spot_response = self.corpay_service.get_spot_rate(data=rate_request_serializer.validated_data)
        fee = self._calculate_fee(spot_response)
        quote_payments_response = self._get_quote_from_mass_payment(
            request_serializer=serializer,
            fee=fee,
            company=request.user.company
        )
        response = self._get_quote_payment_response(
            spot_response,
            quote_payments_response,
            fee
        )
        response_serializer = QuotePaymentResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)

    def _get_quote_from_mass_payment(
        self,
        request_serializer: QuotePaymentSerializer,
        fee: dict,
        company: Company
    ):
        original_payment = QuotePayment(
            beneficiaryId=request_serializer.validated_data.beneficiaryId,
            paymentMethod=request_serializer.validated_data.paymentMethod,
            amount=request_serializer.validated_data.amount,
            lockside=request_serializer.validated_data.lockside,
            paymentCurrency=request_serializer.validated_data.paymentCurrency,
            settlementCurrency=request_serializer.validated_data.settlementCurrency,
            settlementAccountId=request_serializer.validated_data.settlementAccountId,
            settlementMethod=request_serializer.validated_data.settlementMethod,
            paymentReference=request_serializer.validated_data.paymentReference,
            purposeOfPayment=request_serializer.validated_data.purposeOfPayment,
            remitterId=request_serializer.validated_data.remitterId,
            deliveryDate=request_serializer.validated_data.deliveryDate,
            paymentId=request_serializer.validated_data.paymentId
        )
        setting = CorpaySettings.get_settings(company)
        pangea_fee_payment = QuotePayment(
            beneficiaryId=setting.fee_wallet_id,
            paymentMethod='StoredValue',
            amount=fee['amount_usd'],
            lockside=Locksides.Settlement,
            paymentCurrency='USD',
            settlementCurrency=request_serializer.validated_data.settlementCurrency,
            settlementAccountId=request_serializer.validated_data.settlementAccountId,
            settlementMethod=request_serializer.validated_data.settlementMethod,
            purposeOfPayment='PROFESSIONAL FEES PAYMENT',
            paymentReference='Pangea Spot Transaction Fee'
        )
        data = QuotePaymentsBody(payments=[
            original_payment,
            pangea_fee_payment
        ])
        response = self.corpay_service.quote_payments(data=data)
        return response

    def _calculate_fee(self, response: dict):
        fee = CurrencyFee.get_max(
            currencies=[
                response['settlement']['currency'],
                response['payment']['currency']
            ],
            broker=self.broker
        )
        fee_amount = response['settlement']['amount'] * fee
        fee = {
            'fee': fee,
            'amount_settlement': fee_amount,
            'amount_total': fee_amount + response['settlement']['amount'],
            "value": response.get('rate').get('value') + (response.get('rate').get('value') * fee)
        }

        if response['settlement']['currency'] != 'USD':
            # 2nd Call
            # TODO: Use the ICE rate here instead
            data = SpotRateBody(
                paymentCurrency='USD',
                settlementCurrency=response['settlement']['currency'],
                amount=fee_amount,
                lockSide='settlement'
            )
            _response = self.corpay_service.get_spot_rate(data=data)
            fee['amount_usd'] = _response['payment']['amount']
            fee['quote_id'] = _response['quoteId']
        else:
            fee['amount_usd'] = fee['amount_settlement']
        return fee

    def _get_quote_payment_response(
        self,
        spot_response: dict,
        response_data: OrderedDict,
        fee: dict
    ):
        return {
            "rate": {
                "value": fee['value'],
                "lockSide": spot_response.get("rate").get('lockSide'),
                "rateType": spot_response.get("rate").get("rateType"),
                "operation": spot_response.get("rate").get("operation")
            },
            "payment": {
                "currency": spot_response.get("payment").get("currency"),
                "amount": spot_response.get("payment").get("amount")
            },
            "settlement": {
                "currency": spot_response.get("settlement").get("currency"),
                "amount": fee['amount_total']
            },
            "quote": response_data
        }


class CorPayBookPaymentView(CorPayBaseView):
    @extend_schema(
        request=BookPaymentRequestSerializer,
        responses={
            status.HTTP_200_OK: BookPaymentsResponseSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        self.corpay_service.init_company(request.user.company)
        serializer = BookPaymentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = BookPaymentsParams(
            quoteKey=serializer.validated_data.get('quote_id'),
            loginSessionId=serializer.validated_data.get('session_id')
        )
        data = BookPaymentsBody(
            combineSettlements=True
        )
        response = self.corpay_service.book_payments(
            params=params,
            data=data
        )
        response_serializer = BookPaymentsResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)
