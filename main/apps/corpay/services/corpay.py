import abc
import logging
from datetime import timedelta
from typing import Optional, Union, Iterable, Tuple
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from hdlib.DateTime.Date import Date

import redis

from main.apps.account.models import Company
from main.apps.corpay.models import (
    ForwardQuote,
    Locksides,
    CorpaySettings,
    ForwardGuidelines,
    Beneficiary,
    BeneficiaryTemplate,
    Forward,
)
from main.apps.corpay.services.api.connector.auth import CorPayAPIAuthConnector
from main.apps.corpay.services.api.connector.beneficiary import CorPayAPIBeneficiaryConnector
from main.apps.corpay.services.api.connector.forward import CorPayAPIForwardConnector
from main.apps.corpay.services.api.connector.mass_payment import CorPayAPIMassPaymentConnector
from main.apps.corpay.services.api.connector.onboarding import CorPayAPIOnboardingConnector
from main.apps.corpay.services.api.connector.proxy import CorPayAPIProxyConnector
from main.apps.corpay.services.api.connector.settlement_account import CorPayAPISettlementAccountConnector
from main.apps.corpay.services.api.connector.spot import CorPayAPISpotConnector
from main.apps.corpay.services.api.dataclasses.beneficiary import BeneficiaryRulesQueryParams, BeneficiaryRequestBody, \
    BeneficiaryListQueryParams, BankSearchParams, IbanValidationRequestBody
from main.apps.corpay.services.api.dataclasses.forwards import (
    RequestForwardQuoteBody,
    CompleteOrderBody,
    DrawdownBody,
    DrawdownOrder,
    DrawdownPayment,
    DrawdownSettlement, DrawdownPaymentFee
)
from main.apps.corpay.services.api.dataclasses.mass_payment import QuotePaymentsBody, BookPaymentsBody, \
    BookPaymentsParams
from main.apps.corpay.services.api.dataclasses.onboarding import OnboardingRequestBody, OnboardingPickListParams
from main.apps.corpay.services.api.dataclasses.settlement_accounts import ViewFXBalanceAccountsParams, \
    FxBalanceHistoryParams, CreateFXBalanceAccountsBody
from main.apps.corpay.services.api.dataclasses.spot import SpotRateBody, InstructDealBody, PurposeOfPaymentParams
from main.apps.corpay.signals.handlers import call_spot_rate, call_book_spot_deal
from main.apps.currency.models import FxPair, Currency
from main.apps.hedge.models import DraftFxForwardPosition
from main.apps.core.utils.slack import send_exception_to_slack

logger = logging.getLogger(__name__)


class CorPayExecutionService(abc.ABC):
    draft_fx_forward: Optional[DraftFxForwardPosition] = None
    forward_list_cache = None

    def set_draft_fx_forward(self, draft_fx_forward: DraftFxForwardPosition):
        self.draft_fx_forward = draft_fx_forward

    def get_draft_fx_forward(self) -> Optional[DraftFxForwardPosition]:
        return self.draft_fx_forward

    @abc.abstractmethod
    def execute(self, base: Currency, tenor: Date, amount: float, cashflow_id: int) -> Forward:
        """
        Execute a forward transaction

        This method will execute a forward fx transaction on currency pair `base'/`company.currency` with the given
        tenor and amount. The beneficiary will be used to send the funds to the beneficiary.

        - Note that this class takes a base currency rather than an fx pair. The implication of this is that
            implementations have an implicit base currency. This is due to
            1. The fact that CorPayService is stateful and has a company
            2. Companies have a domestic currency and all fx transactions are paid in that currency.

        :param base: the base currency
        :param tenor: the tenor of the forward. This is the date the funds will be delivered to the beneficiary
        :param amount: the amount of the forward in the base currency
        :param cashflow_id: the cashflow id
        :return: the forward quote
        """
        pass

    def drawdown_forward(self, forward: Forward):
        pass

    def request_quote(self, fx_pair: FxPair, amount: float, maturity_date: Date, cashflow_id: int,
                      lock_side: Locksides, save: bool = True) -> ForwardQuote:
        raise NotImplementedError

    def list_forwards(self):
        raise NotImplementedError

    def book_drawdown(self, data: DrawdownBody):
        raise NotImplementedError

    def get_forward_quote(self, data: RequestForwardQuoteBody):
        raise NotImplementedError

    def book_forward_quote(self, quote_id: str):
        raise NotImplementedError

    def complete_order(self, forward_id: int, data: CompleteOrderBody):
        raise NotImplementedError

    def get_spot_rate(self, data: SpotRateBody):
        raise NotImplementedError

    def book_spot_deal(self, quote_id: str):
        raise NotImplementedError

    def instruct_spot_deal(self, data: InstructDealBody):
        raise NotImplementedError

    def quote_payments(self, data: QuotePaymentsBody):
        raise NotImplementedError

    def book_payments(self, params: BookPaymentsParams, data: BookPaymentsBody):
        raise NotImplementedError

    def list_purpose_of_payment(self, data: PurposeOfPaymentParams):
        raise NotImplementedError

    def list_settlement_accounts(self):
        raise NotImplementedError

    def list_fx_balance_accounts(self, data: ViewFXBalanceAccountsParams):
        raise NotImplementedError

    def create_fx_balance_accounts(self, data: CreateFXBalanceAccountsBody):
        raise NotImplementedError

    def list_fx_balance_history(self, fx_balance_id: str, data: FxBalanceHistoryParams):
        raise NotImplementedError

    def get_beneficiary_rules(self, data: BeneficiaryRulesQueryParams):
        raise NotImplementedError

    def upsert_beneficiary(self, data: BeneficiaryRequestBody, company: Company, is_withdraw: bool = False):
        raise NotImplementedError

    def get_beneficiary(self, client_integration_id: str):
        raise NotImplementedError

    def delete_beneficiary(self, client_integration_id: str):
        raise NotImplementedError

    def list_beneficiary(self, data: BeneficiaryListQueryParams):
        raise NotImplementedError

    def list_bank(self, data: BankSearchParams):
        raise NotImplementedError

    def iban_validation(self, data: IbanValidationRequestBody):
        raise NotImplementedError

    def client_onboarding(self, data: OnboardingRequestBody):
        raise NotImplementedError

    def client_onboarding_files(self, client_onboarding_id: str, files: Iterable[Tuple]):
        raise NotImplementedError

    def onboarding_picklist(self, data: OnboardingPickListParams):
        raise NotImplementedError

    def proxy_request(self, url: str, method: str):
        raise NotImplementedError

    def get_client_access_code(self):
        raise NotImplementedError

    def get_partner_access_code(self):
        raise NotImplementedError

    def init_company(self, company: Company):
        raise NotImplementedError

    def get_proxy_url_path(self, url: str):
        raise NotImplementedError


class CorPayExecutionServiceFactory:
    cache = {}

    @classmethod
    def for_company(cls, company: Company) -> 'CorPayService':

        if company.pk in cls.cache:
            return cls.cache[company.pk]
        else:
            service = CorPayService()
            service.company = company
            service.init_company(company)
            cls.cache[company.pk] = service
            return service

    @classmethod
    def clear_cache(cls):
        cls.cache.clear()


class CorPayService(CorPayExecutionService):
    client_access_code: Optional[str] = None
    partner_access_code: Optional[str] = None
    credentials: Optional[CorpaySettings] = None
    company: Optional[Company] = None

    def __init__(self):
        self._connector = {
            'auth': CorPayAPIAuthConnector(),
            'forward': CorPayAPIForwardConnector(),
            'spot': CorPayAPISpotConnector(),
            'mass_payment': CorPayAPIMassPaymentConnector(),
            'settlement_accounts': CorPayAPISettlementAccountConnector(),
            'beneficiary': CorPayAPIBeneficiaryConnector(),
            'proxy': CorPayAPIProxyConnector(),
            'onboarding': CorPayAPIOnboardingConnector()
        }

    def get_quote(self, quote_id: Union[str, int]) -> Optional[ForwardQuote]:
        # if int is a string then lookup by the corpay quote id
        if isinstance(quote_id, str):
            return ForwardQuote.objects.get(quote_id=quote_id)
        elif isinstance(quote_id, int):
            return ForwardQuote.objects.get(id=quote_id)
        else:
            raise ValueError("Invalid quote id")

    def request_quote(
        self,
        fx_pair: FxPair,
        amount: float,
        maturity_date: Date,
        cashflow_id: int,
        lock_side: Locksides,
        save: bool = True
    ) -> ForwardQuote:
        credentials = CorpaySettings.get_settings(self.company)
        if not credentials:
            raise ValueError("No credentials found")

        response = self._connector['auth'].partner_level_token_login()
        partner_access_code = response['access_code']
        response = self._connector['auth'].client_level_token_login(
            user_id=credentials.user_id,
            client_level_signature=credentials.signature,
            partner_access_code=partner_access_code
        )
        client_access_code = response['access_code']

        # Get Forward Guidelines
        logger.debug("Getting forward guidelines........")
        corpay_guidelines = self._connector['forward'].forward_guidelines(
            client_code=credentials.client_code,
            access_code=client_access_code
        )

        # Request Forward Quote
        logger.debug("Requesting forward quote........")
        forward_quote_request = RequestForwardQuoteBody(
            amount=amount,
            buyCurrency=fx_pair.base.get_mnemonic(),
            forwardType='C',
            lockSide='Payment' if lock_side == Locksides.Payment else 'Settlement',
            maturityDate=maturity_date.strftime("%Y-%m-%d"),
            sellCurrency=fx_pair.quote.get_mnemonic()
        )
        corpay_quote = self._connector['forward'].request_forward_quote_with_date_adjustment(
            client_code=credentials.client_code,
            access_code=client_access_code,
            data=forward_quote_request
        )
        guideline = ForwardGuidelines(
            credentials=credentials,
            base_currency=Currency.get_currency(
                corpay_guidelines['baseCurrency']),
            bookdate=Date.fromisoformat(corpay_guidelines['bookDate']),
            forward_maturity_days=corpay_guidelines['forwardMaturityDays'],
            client_limit_amount=corpay_guidelines['clientLimit']["amount"],
            client_limit_currency=Currency.get_currency(
                corpay_guidelines['clientLimit']["currency"]),
            allow_book_deals=corpay_guidelines['allowBookDeals'],
            margin_call_percent=corpay_guidelines['marginCallPercent'],
            max_days=corpay_guidelines['maxDays'],
            hedging_agreement=corpay_guidelines["forwardAgreement"]['hedgingAgreement'],
            allow_book=corpay_guidelines["forwardAgreement"]['allowBook'],
            forward_max_open_contract_interval=corpay_guidelines["forwardMaxOpenContractInterval"]
        )
        quote = ForwardQuote(
            forward_guideline=guideline,
            quote_id=corpay_quote['quoteId'],
            rate_value=corpay_quote['rate']['value'],
            rate_lockside=corpay_quote['rate']['lockSide'],
            rate_type=FxPair.get_pair(corpay_quote['rate']['rateType']),
            rate_operation=corpay_quote['rate']['operation'],
            payment_currency=Currency.get_currency(
                corpay_quote["payment"]["currency"]),
            payment_amount=corpay_quote['payment']['amount'],
            settlement_currency=Currency.get_currency(
                corpay_quote['settlement']['currency']),
            settlement_amount=corpay_quote['settlement']['amount'],
            cashflow_id=cashflow_id
        )
        if save:
            guideline.save()
            quote.save()

        return quote

    def execute_quote(self, quote: ForwardQuote) -> Forward:
        draft_fx_forward = self.get_draft_fx_forward()
        response = self._connector["forward"].book_forward_quote(
            client_code=self.credentials.client_code,
            access_code=self.get_client_access_code(),
            quote_id=quote.quote_id)
        forward_id = response["forwardId"]

        forward_instruction_response = self._connector["forward"].forward(
            client_code=self.credentials.client_code,
            access_code=self.get_client_access_code(),
            forward_id=forward_id
        )

        complete_order = CompleteOrderBody(
            settlementAccount=draft_fx_forward.funding_account,
            forwardReference=f"Cashflow {quote.cashflow_id}",
        )

        self._connector["forward"].complete_order(
            client_code=self.credentials.client_code,
            access_code=self.get_client_access_code(),
            forward_id=forward_id,
            data=complete_order,
        )

        return Forward.objects.create(
            forward_quote=quote,
            corpay_forward_id=response['forwardId'],
            order_number=response['orderNumber'],
            token=response['token'],
            origin_account=draft_fx_forward.origin_account,
            destination_account=draft_fx_forward.destination_account,
            funding_account=draft_fx_forward.funding_account,
            cash_settle_account=draft_fx_forward.cash_settle_account,
            is_cash_settle=draft_fx_forward.is_cash_settle,
            purpose_of_payment=draft_fx_forward.purpose_of_payment,
            maturity_date=Date.fromisoformat(
                forward_instruction_response['maturityDate'])
        )

    def drawdown_forward(self, forward: Forward):
        if forward.destination_account is None:
            logger.error(
                f"No destination account set for forward: {forward.id}")
            return
        if forward.origin_account is None:
            logger.error(f"No origin account set for forward: {forward.id}")
            return
        forward.drawdown_date = Date.today()
        _forward = self.get_forward_details(forward.corpay_forward_id)
        if _forward is None:
            logger.error(
                f"Unable to find a forward on Corpay for forward: {forward.pk}")
            return
        if _forward['statusDesc'] != 'Available':
            logger.error(
                f"Forward has already been drawndown skipping forward: {forward.pk}")
            return
        drawdown_order = DrawdownOrder(
            orderId=_forward['ordNum'],
            amount=_forward['amount']
        )
        drawdown_fee = DrawdownPaymentFee(
            expectataion='AnyFee',
            amount=0,
            currency=_forward['costCurrency']
        )
        drawdown_payment = DrawdownPayment(
            beneficiaryId=forward.destination_account,
            deliveryMethod=forward.destination_account_type,
            amount=_forward['availableBalance'],
            currency=_forward['currency'],
            purposeOfPayment=forward.purpose_of_payment,
            fee=drawdown_fee
        )
        drawdown_settlement = DrawdownSettlement(
            accountId=forward.origin_account,
            deliveryMethod='C',
            currency=_forward['costCurrency'],
            purpose='Drawdown'
        )
        drawdown_body = DrawdownBody(
            orders=[
                drawdown_order
            ],
            payments=[
                drawdown_payment
            ],
            settlements=[
                drawdown_settlement
            ]
        )
        response = self.book_drawdown(data=drawdown_body)
        forward.drawdown_order_number = response['ordNum']
        forward.save()
        return forward

    def list_forwards(self):
        client_access_code = self.get_client_access_code()
        response = self._connector['forward'].forwards(
            client_code=self.credentials.client_code,
            access_code=client_access_code
        )
        return response

    def list_spot_orders(self):
        client_access_code = self.get_client_access_code()
        response = self._connector['spot'].list_orders(
            client_code=self.credentials.client_code,
            access_code=client_access_code
        )
        return response

    def get_forward_cache(self):
        cache_key = f'corpay-fwd-details-{self.company.pk}'
        data = None
        try:
            data = cache.get(cache_key)
            cache_valid = True
        except redis.exceptions.ConnectionError:
            logger.error('cannot connect to redis!!!')
            send_exception_to_slack('cannot connect to redis!!!')
            data = None
            cache_valid = False

        if data is None:
            response = self.list_forwards()
            if response:
                data = {}
                for forward in response['data']['rows']:
                    data[forward['forwardId']] = forward
            now = Date.now()
            expire_at = Date.today()+timedelta(days=1, hours=8)
            expires_in = int((expire_at-now).total_seconds())
            cache.set(cache_key, data, expires_in)

        return data

    def get_forward_details(self, forward_id):
        client_access_code = self.get_client_access_code()
        data = self.get_forward_cache()
        if data:
            return data.get(str(forward_id))
        return

        response = self._connector['forward'].forward(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            forward_id=forward_id
        )

        return response

    def get_order_details(self, order_number):
        client_access_code = self.get_client_access_code()
        response = self._connector['spot'].lookup_orders(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            order_number=order_number
        )
        return response

    def book_drawdown(self, data: DrawdownBody):
        client_access_code = self.get_client_access_code()
        response = self._connector['forward'].book_drawdown(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            data=data
        )
        return response

    def execute(self, base_currency: Currency, tenor: Date, amount: float, cashflow_id: int) -> Forward:
        if amount > 0:
            quote_currency = self.company.currency
            base_currency = base_currency
            lock_side = Locksides.Payment
        else:
            quote_currency = base_currency
            base_currency = self.company.currency
            lock_side = Locksides.Settlement
        pair = FxPair.get_pair_from_currency(base_currency, quote_currency)

        # we take the absolute value of the amount since the base/quote has been adjusted to always be
        # long the quote currency.
        quote = self.request_quote(
            pair, abs(amount), tenor, cashflow_id, lock_side, True)
        forward = self.execute_quote(quote)
        return forward

    def get_forward_quote(self, data: RequestForwardQuoteBody):
        client_access_code = self.get_client_access_code()
        response = self._connector['forward'].request_forward_quote(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            data=data
        )
        return response

    def book_forward_quote(self, quote_id: str):
        client_access_code = self.get_client_access_code()
        response = self._connector['forward'].book_forward_quote(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            quote_id=quote_id
        )
        return response

    def complete_order(self, forward_id: int, data: CompleteOrderBody):
        client_access_code = self.get_client_access_code()
        response = self._connector['forward'].complete_order(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            forward_id=forward_id,
            data=data
        )
        return response

    def get_spot_rate(self, data: SpotRateBody):
        client_access_code = self.get_client_access_code()
        response = self._connector['spot'].spot_rate(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            data=data
        )
        call_spot_rate.send(sender=None, response_content=response)

        return response

    def book_spot_deal(self, quote_id: str):
        client_access_code = self.get_client_access_code()
        response = self._connector['spot'].book_deal(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            quote_id=quote_id
        )
        call_book_spot_deal.send(
            sender=None, quote_id=quote_id, order_number=response['orderNumber'])

        return response

    def instruct_spot_deal(self, data: InstructDealBody):
        client_access_code = self.get_client_access_code()
        response = self._connector['spot'].instruct_deal(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            data=data
        )
        return response

    def quote_payments(self, data: QuotePaymentsBody):
        client_access_code = self.get_client_access_code()
        response = self._connector['mass_payment'].quote_payments(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            data=data
        )
        return response

    def book_payments(self, params: BookPaymentsParams, data: BookPaymentsBody):
        client_access_code = self.get_client_access_code()
        response = self._connector['mass_payment'].book_payments(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            quote_id=params.quoteKey,
            session_id=params.loginSessionId,
            data=data
        )
        return response

    def list_purpose_of_payment(self, data: PurposeOfPaymentParams):
        client_access_code = self.get_client_access_code()
        response = self._connector['spot'].purpose_of_payment(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            data=data
        )
        return response

    def list_settlement_accounts(self):
        client_access_code = self.get_client_access_code()
        response = self._connector['settlement_accounts'].settlement_accounts(
            client_code=self.credentials.client_code,
            access_code=client_access_code
        )
        return response

    def list_fx_balance_accounts(self, data: ViewFXBalanceAccountsParams):
        client_access_code = self.get_client_access_code()
        response = self._connector['settlement_accounts'].fx_balance_accounts(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            data=data
        )
        return response

    def create_fx_balance_accounts(self, data: CreateFXBalanceAccountsBody):
        client_access_code = self.get_client_access_code()
        response = self._connector['settlement_accounts'].create_fx_balance_accounts(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            data=data
        )
        return response

    def list_fx_balance_history(self, fx_balance_id: str, data: FxBalanceHistoryParams):
        client_access_code = self.get_client_access_code()
        response = self._connector['settlement_accounts'].fx_balance_history(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            fx_balance_id=fx_balance_id,
            data=data
        )
        return response

    def get_beneficiary_rules(self, data: BeneficiaryRulesQueryParams):
        client_access_code = self.get_client_access_code()
        response = self._connector['beneficiary'].beneficiary_rules(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            data=data
        )
        return response

    @transaction.atomic
    def upsert_beneficiary(self, data: BeneficiaryRequestBody, company: Company, is_withdraw: bool = False):
        if data.templateIdentifier:
            client_integration_id = data.templateIdentifier
            beneficiary = Beneficiary.get_beneficiary_by_client_integration_id(
                integration_id=data.templateIdentifier,
                company=company
            )
        else:
            beneficiary = Beneficiary.create_beneficiary_for_company(
                company, is_withdraw)
            client_integration_id = beneficiary.client_integration_id
        client_access_code = self.get_client_access_code()
        response = self._connector['beneficiary'].upsert_beneficiary(
            client_code=self.credentials.client_code,
            client_integration_id=client_integration_id,
            access_code=client_access_code,
            data=data
        )
        if 'templateId' in response:
            beneficiary_template = BeneficiaryTemplate(
                template_id=response['templateId'],
                beneficiary=beneficiary[0] if isinstance(
                    beneficiary, tuple) else beneficiary
            )
            beneficiary_template.save()
        response['client_integration_id'] = client_integration_id
        return response

    def get_beneficiary(self, client_integration_id: str):
        client_access_code = self.get_client_access_code()
        response = self._connector['beneficiary'].get_beneficiary(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            client_integration_id=client_integration_id
        )
        return response

    def delete_beneficiary(self, client_integration_id: str):
        client_access_code = self.get_client_access_code()
        response = self._connector['beneficiary'].delete_beneficiary(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            client_integration_id=client_integration_id
        )
        return response

    def list_beneficiary(self, data: BeneficiaryListQueryParams):
        client_access_code = self.get_client_access_code()
        response = self._connector['beneficiary'].list_beneficiary(
            client_code=self.credentials.client_code,
            access_code=client_access_code,
            data=data
        )
        return response

    def list_bank(self, data: BankSearchParams):
        client_access_code = self.get_client_access_code()
        response = self._connector['beneficiary'].list_bank(
            access_code=client_access_code,
            data=data
        )
        return response

    def iban_validation(self, data: IbanValidationRequestBody):
        client_access_code = self.get_client_access_code()
        response = self._connector['beneficiary'].iban_validation(
            access_code=client_access_code,
            data=data
        )
        return response

    def client_onboarding(self, data: OnboardingRequestBody):
        partner_access_code = self.get_partner_access_code()
        response = self._connector['onboarding'].client_onboarding(
            access_code=partner_access_code,
            data=data
        )
        return response

    def client_onboarding_files(self, client_onboarding_id: str, files: Iterable[Tuple]):
        partner_access_code = self.get_partner_access_code()
        response = self._connector['onboarding'].client_onboarding_files(
            access_code=partner_access_code,
            client_onboarding_id=client_onboarding_id,
            files=files
        )
        return response

    def onboarding_picklist(self, data: OnboardingPickListParams):
        partner_access_code = self.get_partner_access_code()
        response = self._connector['onboarding'].onboarding_picklist(
            access_code=partner_access_code,
            data=data
        )
        return response

    def proxy_request(self, url: str, method: str):
        client_access_code = self.get_client_access_code()
        response = self._connector['proxy'].proxy_request(
            url=url,
            method=method,
            access_code=client_access_code
        )
        if 'content' not in response:
            return response
        self._process_proxy_response(url, response)
        return response['content']

    def get_client_access_code(self):
        if not self.credentials:
            raise ValueError("No credentials found")
        cache_key = f'{settings.APP_ENVIRONMENT}-corpay-client_access_token-{self.company.pk}'

        try:
            cached_data = cache.get(cache_key)
            cache_valid = True
        except redis.exceptions.ConnectionError:
            logger.error('cannot connect to redis!!!')
            send_exception_to_slack('cannot connect to redis!!!')
            cached_data = None
            cache_valid = False
        if cached_data:
            return cached_data['access_code']
        partner_access_code = self.get_partner_access_code()
        now = Date.now()
        response = self._connector['auth'].client_level_token_login(
            user_id=self.credentials.user_id,
            client_level_signature=self.credentials.signature,
            partner_access_code=partner_access_code
        )
        access_code = response['access_code']
        expires_in = response['expires_in']
        expiration_time = now + timedelta(seconds=expires_in)
        if cache_valid:
            cache.set(cache_key, {'access_code': access_code,
                      'expires_in': expiration_time}, expires_in)
        return access_code

    def get_partner_access_code(self):
        cache_key = f'{settings.APP_ENVIRONMENT}-corpay-partner_access_token'
        cached_data = cache.get(cache_key)
        if cached_data:
            # if the access code is cached, return it
            return cached_data['access_code']
        now = Date.now()
        response = self._connector['auth'].partner_level_token_login()
        access_code = response['access_code']
        expires_in = response['expires_in']
        expiration_time = now + timedelta(seconds=expires_in)
        cache.set(cache_key, {'access_code': access_code,
                  'expires_in': expiration_time}, expires_in)
        return access_code

    def init_company(self, company: Company):
        self.company = company
        self.credentials = CorpaySettings.get_settings(company)
        self.client_access_code = None
        self.partner_access_code = None

    def _process_proxy_response(self, url: str, response: dict):
        value_set = []
        content = response['content']
        last_part = self.get_proxy_url_path(url)
        if last_part == 'regions':
            if 'regions' not in content:
                return response
            regions = content['regions']
            for region in regions:
                value_set.append({
                    'id': region['id'],
                    'text': region['name']
                })
            content['valueSet'] = value_set
        if last_part == 'countries':
            for country in content:
                value_set.append({
                    'id': country['country'],
                    'text': country['countryName']
                })
            new_content = {
                'countries': content,
                'valueSet': value_set
            }
            response['content'] = new_content
        if last_part == 'payCurrencies':
            if 'all' not in content:
                return response
            currencies = content['all']
            for currency in currencies:
                value_set.append({
                    'id': currency['curr'],
                    'text': currency['desc']
                })
            content['valueSet'] = value_set
        return response

    def get_proxy_url_path(self, url: str):
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.split('/')
        last_part = path_parts[-1]
        # TODO: Need to refactor to support this kind of url: https://crossborder.beta.corpay.com/api/268780/0/settlementAccount/INCOMING268780_CAD/W/CAD
        return last_part
