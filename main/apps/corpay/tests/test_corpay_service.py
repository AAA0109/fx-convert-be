import json
import re
from datetime import datetime, timezone, timedelta
import unittest

from django.conf import settings
from django.test import TestCase
import logging
from pprint import pformat

from main.apps.core.tests.base import BaseTestCase
from main.apps.corpay.services.api.connector.auth import CorPayAPIAuthConnector
from main.apps.corpay.services.api.connector.beneficiary import CorPayAPIBeneficiaryConnector
from main.apps.corpay.services.api.connector.forward import CorPayAPIForwardConnector
from main.apps.corpay.services.api.connector.spot import CorPayAPISpotConnector
from main.apps.corpay.services.api.dataclasses.beneficiary import BeneficiaryRulesQueryParams
from main.apps.corpay.services.api.dataclasses.forwards import RequestForwardQuoteBody, CompleteOrderBody
from main.apps.corpay.services.api.dataclasses.spot import SpotRateBody, InstructDealOrder, InstructDealPayment, \
    InstructDealSettlement, InstructDealBody
from main.apps.corpay.services.api.exceptions import BadRequest

logger = logging.getLogger(__name__)


class CorPayConnectorTestCase(BaseTestCase):
    @unittest.skipIf(not settings.CORPAY_RUN_TESTS, "Only run if CORPAY_RUN_TESTS is set to True")
    def test_forward_integration(self):
        client_access_code = self._get_client_access_code()

        # Get Forward Guidelines
        logger.debug("Getting forward guidelines........")
        response = self.api['forward'].forward_guidelines(client_code=self.client_code, access_code=client_access_code)
        logger.debug(pformat(response))

        # Request Forward Quote
        logger.debug("Requesting forward quote........")
        now = datetime.now(tz=timezone.utc)
        maturity_date = self.api['forward'].nearest_weekday(now, 30)
        date_format = "%Y-%m-%d"
        forward_quote_request = RequestForwardQuoteBody(
            amount=1000,
            buyCurrency='EUR',
            forwardType='C',
            lockSide='settlement',
            maturityDate=maturity_date.strftime(date_format),
            sellCurrency='CAD'
        )
        response = self.api['forward'].request_forward_quote(client_code=self.client_code,
                                                             access_code=client_access_code,
                                                             data=forward_quote_request)
        logger.debug(pformat(response))
        quote_id = response['quoteId']

        # Book forward
        logger.debug("Booking forward........")
        response = self.api['forward'].book_forward_quote(client_code=self.client_code, access_code=client_access_code,
                                                          quote_id=quote_id)
        logger.debug(pformat(response))
        content = response
        forward_id = content['forwardId']


        # Complete Order
        logger.debug("Completing Order........")
        complete_order = CompleteOrderBody(
            settlementAccount=self.settlement_accounts['cad']['wire'],
            forwardReference=f'Integration Test {datetime.now()}'
        )
        response = self.api['forward'].complete_order(client_code=self.client_code, access_code=client_access_code,
                                                      forward_id=forward_id, data=complete_order)
        logger.debug(pformat(response))
        self.assertIn('forwardId', response)
        self.assertIn('orderNumber', response)

    @unittest.skipIf(not settings.CORPAY_RUN_TESTS, "Only run if CORPAY_RUN_TESTS is set to True")
    def test_spot_integration(self):
        client_access_code = self._get_client_access_code()

        # Get Spot Rate
        logger.debug("Getting Spot Rate........")
        spot_rate_body = SpotRateBody(
            paymentCurrency='GBP',
            settlementCurrency='USD',
            amount=10000,
            lockSide='payment'
        )
        response = self.api['spot'].spot_rate(client_code=self.client_code, access_code=client_access_code,
                                              data=spot_rate_body)
        logger.debug(pformat(response))
        spot_rate_response = response
        quote_id = spot_rate_response['quoteId']

        # Book Deal
        logger.debug("Booking Deal........")
        response = self.api['spot'].book_deal(client_code=self.client_code, access_code=client_access_code,
                                              quote_id=quote_id)
        logger.debug(pformat(response))
        content = response
        order_number = content['orderNumber']

        # Instruct Deal
        logger.debug("Instructing Deal........")
        order = InstructDealOrder(
            orderId=order_number,
            amount=spot_rate_response['payment']['amount']
        )
        payment = InstructDealPayment(
            amount=spot_rate_response['payment']['amount'],
            beneficiaryId=self.fx_balance_accounts['gbp'],
            deliveryMethod='C',
            currency=spot_rate_response['payment']['currency'],
            purposeOfPayment='PURCHASE OF GOOD(S)'
        )
        settlement = {
            "spot": InstructDealSettlement(
                accountId=self.fx_balance_accounts['usd'],
                deliveryMethod='C',
                currency=spot_rate_response['payment']['currency'],
                purpose='Spot'
            ),
            "fee": InstructDealSettlement(
                accountId=self.fx_balance_accounts['gbp'],
                deliveryMethod='C',
                currency=spot_rate_response['settlement']['currency'],
                purpose='Fee'
            )
        }
        instruct_deal_body = InstructDealBody(
            orders=[
                order
            ],
            payments=[
                payment
            ],
            settlements=[
                settlement['spot'],
                settlement['fee']
            ]
        )

        response = self.api['spot'].instruct_deal(client_code=self.client_code, access_code=client_access_code,
                                                  data=instruct_deal_body)
        logger.debug(pformat(response))
        self.assertIn('ordNum', response)

    @unittest.skipIf(not settings.CORPAY_RUN_TESTS, "Only run if CORPAY_RUN_TESTS is set to True")
    def test_get_beneficiary_rules(self):
        params = BeneficiaryRulesQueryParams(
            destinationCountry='US',
            bankCountry='US',
            bankCurrency='USD',
            classification='business',
            paymentMethods='W'
        )
        client_access_code = self._get_client_access_code()
        response = self.api['beneficiary'].beneficiary_rules(client_code=self.client_code,
                                                             access_code=client_access_code,
                                                             data=params)
        logger.debug(pformat(response))

    def _get_client_access_code(self):
        response = self.api['auth'].partner_level_token_login()
        partner_access_code = response['access_code']
        response = self.api['auth'].client_level_token_login(
            user_id=self.client_user_id,
            client_level_signature=self.client_level_signature,
            partner_access_code=partner_access_code
        )
        client_access_code = response['access_code']
        return client_access_code

    def _request_forward_quote(self, access_code: str, data: RequestForwardQuoteBody, now: datetime, tenor: int):
        should_try_request = True
        while should_try_request:
            try:
                should_try_request = False
                response_ask = self.api['forward'].request_forward_quote(client_code=self.client_code,
                                                                         access_code=access_code,
                                                                         data=data)
                return response_ask
            except BadRequest as e:
                for arg in e.args:
                    for error in arg['errors']:
                        if error['key'] == 'WeekendHolidayCheck':
                            logger.debug(f"{error['message']} - setting maturity to next valid date")
                            regex = r"The maturity date is not valid. The next valid date is ([0-9\-]+)"
                            matches = re.search(regex, error['message'])
                            if matches:
                                for group_num in range(0, len(matches.groups())):
                                    group_num = group_num + 1
                                    maturity_date = matches.group(group_num)
                                    data.maturityDate = maturity_date
                                    should_try_request = True
                        else:
                            logger.error(f"{error['key']} - {error['message']}")
                            should_try_request = False
            except Exception as e:
                logger.error(f"Unable to get forward quote {e}")
