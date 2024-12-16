import json
import logging
from abc import ABC

from main.apps.account.models import Company
from main.apps.corpay.api.serializers.spot.book_instruct_deal import BookInstructDealRequestSerializer
from main.apps.corpay.models import CorpaySettings
from main.apps.corpay.services.api.dataclasses.settlement_accounts import ViewFXBalanceAccountsParams
from main.apps.corpay.services.api.dataclasses.spot import SpotRateBody, InstructDealOrder, InstructDealPayment, \
    InstructDealSettlement, InstructDealBody
from main.apps.corpay.services.corpay import CorPayService
from main.apps.corpay.services.fxbalance.balance import CorPayFXBalanceDraftService

logger = logging.getLogger(__name__)


class CorPayFXBalanceSweepService(ABC):
    def __init__(self):
        self.corpay_service = CorPayService()

    def execute(self, company_id=None):
        settings = CorpaySettings.objects.all()
        if company_id:
            settings = settings.filter(company_id=company_id)
        for setting in settings:
            if setting.fee_wallet_id is None:
                logger.info(f"No fee wallet for company {setting.company.pk}")
                continue
            if setting.pangea_beneficiary_id is None:
                logger.info(f"No Pangea Beneficiary setup for company {setting.company.pk}")
                continue
            company = setting.company
            try:
                self.handle_single(company, setting)
            except Exception as e:
                logger.exception(e)

    def handle_single(self, company: Company, setting: CorpaySettings):
        self.corpay_service.init_company(company)
        logger.info(f"Checking fee wallet balance for company {company.name} ({company.pk}) ")
        balance = self.get_balance(setting)
        if balance > 0:
            self.sweep_balance(company, balance, setting)
        else:
            logger.info(f"No balance for company {company.name} ({company.pk}) ")
            return

    def get_balance(self, setting: CorpaySettings):
        params = ViewFXBalanceAccountsParams(includeBalance=True)
        response = self.corpay_service.list_fx_balance_accounts(params)
        for item in response['items']:
            if item['id'] == setting.fee_wallet_id:
                return item['availableBalance']
        return 0.0

    def sweep_balance(self, company: Company, amount: float, setting: CorpaySettings, settlement_currency='USD',
                      payment_currency='USD'):
        logger.info(f"Company fee wallet has a balance of {amount}, starting the sweeping process")
        # Quote
        logger.info(f"Requesting spot quote...")
        quote_request = self.build_quote_data(amount, settlement_currency, payment_currency)
        logger.info(f"Request: ")
        logger.info(f"{json.dumps(quote_request.json(), indent=4)}")
        quote_response = self.corpay_service.get_spot_rate(data=quote_request)
        logger.info(f"Response: ")
        logger.info(f"{json.dumps(quote_response, indent=4)}")


        # Book deal
        logger.info(f"Booking deal...")
        book_request = self.build_book_data(quote_response, setting.fee_wallet_id, setting.pangea_beneficiary_id)
        logger.info(f"Request: ")
        logger.info(f"{json.dumps(book_request, indent=4)}")
        book_response = self.corpay_service.book_spot_deal(quote_id=quote_response['quoteId'])
        logger.info(f"Response: ")
        logger.info(f"{json.dumps(book_response, indent=4)}")


        # Instruct
        logger.info(f"Instructing deal...")
        instruct_request = self.build_instruct_data(book_request, book_response['orderNumber'])
        logger.info(f"Request: ")
        logger.info(f"{json.dumps(instruct_request.json(), indent=4)}")
        instruct_response = self.corpay_service.instruct_spot_deal(data=instruct_request)
        logger.info(f"Response: ")
        logger.info(f"{json.dumps(instruct_response, indent=4)}")

        logger.info(f"Updating FX Balance transaction history...")
        CorPayFXBalanceDraftService().create(company, instruct_response)

    @staticmethod
    def build_quote_data(amount, settlement_currency, payment_currency) -> SpotRateBody:
        return SpotRateBody(
            lockSide='settlement',
            paymentCurrency=payment_currency,
            settlementCurrency=settlement_currency,
            amount=amount
        )

    @staticmethod
    def build_book_data(quote_response, settlement_account, payment_account):
        data = {
            "book_request": {
                "quote_id": quote_response['quoteId']
            },
            "instruct_request": {
                "orders": [
                    {
                        "amount": quote_response['payment']['amount']
                    }
                ],
                "payments": [
                    dict(
                        beneficiary_id=payment_account,
                        amount=quote_response['payment']['amount'],
                        delivery_method="E",
                        currency=quote_response['payment']['currency'],
                        purpose_of_payment="Pangea Fee",
                        payment_reference="Wallet Transfer",
                    )
                ],
                "settlements": [
                    dict(
                        account_id=settlement_account,
                        delivery_method="C",
                        currency=quote_response['settlement']['currency'],
                        purpose="Spot"
                    ),
                    dict(
                        account_id=settlement_account,
                        delivery_method="C",
                        currency=quote_response['settlement']['currency'],
                        purpose="Fee"
                    ),
                ]
            }
        }
        serializer = BookInstructDealRequestSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    @staticmethod
    def build_instruct_data(book_request, order_number):
        instruct_request = book_request.get('instruct_request')

        orders = []
        for order in instruct_request.get('orders'):
            orders.append(
                InstructDealOrder(
                    orderId=order_number,
                    amount=order.get('amount')
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
        return data
