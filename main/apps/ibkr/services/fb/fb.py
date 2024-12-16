import logging
import xml.etree.ElementTree as ET
from abc import ABC
from typing import OrderedDict, List

from django.db import transaction
from hdlib.DateTime.Date import Date

from main.apps.broker.models import BrokerAccount
from main.apps.currency.models import Currency
from main.apps.ibkr.models import FundingRequest, FundingRequestStatus, FundingRequestProcessingStat, \
    FundingRequestResult, DepositResult, WithdrawResult
from main.apps.ibkr.services.fb.connector import IBFBConnector

logger = logging.getLogger(__name__)


class IBFBService(ABC):
    _connector = None
    ns = {'fbrs': 'http://www.interactivebrokers.com/fbfb_result_set'}

    @property
    def connector(self):
        if self._connector is None:
            self._connector = IBFBConnector()
        return self._connector

    @staticmethod
    def initialize_funding_request(broker_account: BrokerAccount, method: str) -> FundingRequest:
        unsubmitted_requests = FundingRequest.objects.filter(request_submitted=False,
                                                             broker_account=broker_account,
                                                             method=method).order_by('-created')
        if unsubmitted_requests.count() > 0:
            funding_request = unsubmitted_requests.first()
        else:
            with transaction.atomic():
                funding_request = FundingRequest(
                    method=method,
                    broker_account=broker_account
                )
                funding_request.save()
                funding_request_status = FundingRequestStatus(funding_request=funding_request)
                funding_request_status.save()
                funding_request_processing_stats = FundingRequestProcessingStat(funding_request=funding_request)
                funding_request_processing_stats.save()
        return funding_request

    @staticmethod
    def initialize_deposit_result(data: OrderedDict, funding_request: FundingRequest) -> DepositResult:
        deposit_result = DepositResult(
            funding_request=funding_request,
            amount=data.get('amount'),
            currency=Currency.get_currency(data.get('currency')),
            method=data.get('method'),
            saved_instruction_name=data.get('saved_instruction_name')
        )
        deposit_result.save()
        return deposit_result

    @staticmethod
    def initialize_withdraw_result(self, data: OrderedDict, funding_request: FundingRequest) -> WithdrawResult:
        withdraw_result = WithdrawResult(
            funding_request=funding_request,
            amount=data.get('amount'),
            currency=Currency.get_currency(data.get('currency')),
            method=data.get('method'),
            saved_instruction_name=data.get('saved_instruction_name')
        )
        withdraw_result.save()
        return withdraw_result

    def deposit_funds(self, data: OrderedDict) -> FundingRequest:
        broker_account = BrokerAccount.objects.get(pk=data.get('broker_account_id'))
        funding_request = IBFBService.initialize_funding_request(broker_account, 'deposit_funds')
        self.initialize_deposit_result(data, funding_request)
        status_code, response = self.connector.deposit_funds(broker_account.broker_account_name, funding_request.pk,
                                                             data)
        funding_request = self._handle_response(status_code, response, funding_request, 'deposit_funds')

        return funding_request

    def withdraw_funds(self, data: OrderedDict) -> FundingRequest:
        broker_account = BrokerAccount.objects.get(pk=data['broker_account_id'])
        funding_request = IBFBService.initialize_funding_request(broker_account, 'withdraw_funds')
        self.initialize_withdraw_result(data, funding_request)
        status_code, response = self.connector.withdraw_funds(broker_account.broker_account_name, funding_request.pk,
                                                              data)
        funding_request = self._handle_response(status_code, response, funding_request, 'withdraw_funds')
        return funding_request

    def get_instruction_name(self, broker_account_id: int, data: OrderedDict):
        broker_account = BrokerAccount.objects.get(pk=broker_account_id)
        funding_request = IBFBService.initialize_funding_request(broker_account, 'get_instruction_name')
        method = data['method']
        status_code, response = self.connector.get_instruction_name(broker_account.broker_account_name,
                                                                    funding_request.pk,
                                                                    method)
        funding_request = self._handle_response(status_code, response, funding_request, 'get_instruction_name')

        return funding_request

    def predefined_destination_instruction(self, data: OrderedDict):
        broker_account = BrokerAccount.objects.get(pk=data.get('broker_account_id'))
        funding_request = IBFBService.initialize_funding_request(broker_account,
                                                                 'predefined_destination_instruction')
        status_code, response = self.connector.predefined_destination_instruction(
            broker_account.broker_account_name,
            funding_request.pk,
            data
        )
        funding_request = self._handle_response(status_code, response, funding_request,
                                                'predefined_destination_instruction')
        return funding_request

    def get_status(self, instruction_set_id: int) -> FundingRequest:
        funding_request = FundingRequest.objects.get(pk=instruction_set_id)
        status_code, response = self.connector.get_status(instruction_set_id)
        return self._handle_response(status_code, response, funding_request, funding_request.method)

    def get_updated_upload_ids(self, date: Date) -> List[int]:
        status_code, response = self.connector.get_updated_upload_ids(date)
        ids = []
        if status_code == 200:
            if response['request_status'] == "REQUEST_ACCEPTED_FOR_PROCESSING":
                details = self.connector.decode_and_decrypt_data(response['details'])
                details = self.connector.decode_btye_str(details)
                details = details.replace("updated_instruction_set_ids:", "")
                if details == "":
                    return ids
                ids_str = details.split(",")
                ids = [int(x) for x in ids_str]
        return ids

    def _handle_response(self, status_code: int, response: OrderedDict, funding_request: FundingRequest,
                         method: str) -> FundingRequest:
        funding_request_status = funding_request.status
        funding_request_processing_stat = funding_request.processing_stat

        if status_code == 200:
            with transaction.atomic():
                funding_request.request_submitted = True
                funding_request.save()
            if 'processing_stats' in response:
                processing_stats = response['processing_stats']
                funding_request_processing_stat.instruction_set_id = processing_stats['instruction_set_id']
                funding_request_processing_stat.trans_provided = processing_stats['trans_provided']
                funding_request_processing_stat.trans_read = processing_stats['trans_read']
                funding_request_processing_stat.trans_understood = processing_stats['trans_understood']
                funding_request_processing_stat.trans_rejected = processing_stats['trans_rejected']
                funding_request_processing_stat.save()
            if 'error_code' in response:
                with transaction.atomic():
                    funding_request_status.error_code = response['error_code']
                    funding_request_status.error_message = response['error_message']
                    funding_request_status.save()
            elif 'details':
                details_xml = self.connector.decode_and_decrypt_data(response['details'])
                details_xml = self.connector.decode_btye_str(details_xml)
                details_tree = ET.ElementTree(ET.fromstring(details_xml))
                details_root = details_tree.getroot()
                with transaction.atomic():
                    funding_request_status.timestamp = response['timestamp'].replace('-', ' ').replace('.', '-')
                    funding_request_status.request_status = response['request_status']
                    funding_request_status.details = response['details']
                    funding_request_status.save()
                    if method == 'deposit_funds':
                        self._handle_deposit_funds_response(funding_request, details_root)
                    if method == 'get_instruction_name':
                        self._handle_instruction_name(funding_request, details_root)
                    if method == 'get_status':
                        self._handle_get_status(funding_request, details_root)
        return funding_request

    def _handle_deposit_funds_response(self, funding_request: FundingRequest, details_root: ET.Element):
        deposit_result = details_root.find('./fbrs:deposit_result', self.ns)
        result = details_root.find('./fbrs:result', self.ns)
        if deposit_result is not None:
            try:
                deposit_result_model = funding_request.deposit_result
            except AttributeError as e:
                deposit_result_model = DepositResult(funding_request=funding_request)
            # if status is terminal status, skip update
            if deposit_result_model.status in [DepositResult.Status.PROCESSED, DepositResult.Status.REJECTED]:
                logger.debug(
                    f"deposit_result {deposit_result_model.pk} "
                    f"for funding request {funding_request.pk} "
                    f"has a status of '{deposit_result_model.status}', "
                    f"skipping update"
                )
                return
            deposit_ib_instr_id = details_root.find('./fbrs:deposit_result/fbrs:ib_instr_id', self.ns)
            deposit_status = details_root.find('./fbrs:deposit_result/fbrs:status', self.ns)
            deposit_code = details_root.find('./fbrs:deposit_result/fbrs:code', self.ns)
            deposit_description = details_root.find('./fbrs:deposit_result/fbrs:description', self.ns)
            if deposit_ib_instr_id is not None and deposit_ib_instr_id.text is not None:
                deposit_result_model.ib_instr_id = deposit_ib_instr_id.text
            if deposit_status is not None and deposit_status.text is not None:
                deposit_result_model.status = deposit_status.text.lower()
            if deposit_code is not None and deposit_code.text is not None:
                deposit_result_model.code = deposit_code.text
            if deposit_description is not None and deposit_description.text is not None:
                deposit_result_model.description = deposit_description.text
            deposit_result_model.save()
        if result is not None:
            try:
                result_model = funding_request.result
            except AttributeError as e:
                result_model = FundingRequestResult(funding_request=funding_request)
            if result_model.status in [FundingRequestResult.Status.PROCESSED, FundingRequestResult.Status.REJECTED]:
                logger.debug(
                    f"funding request result {result_model.pk} "
                    f"for funding request {funding_request.pk} "
                    f"has a status of '{result_model.status}', "
                    f"skipping update"
                )
                return
            result_ib_instr_id = details_root.find('./fbrs:result/fbrs:ib_instr_id', self.ns)
            result_status = details_root.find('./fbrs:result/fbrs:status', self.ns)
            result_code = details_root.find('./fbrs:result/fbrs:code', self.ns)
            result_description = details_root.find('./fbrs:result/fbrs:description', self.ns)
            if result_ib_instr_id is not None and result_ib_instr_id.text is not None:
                result_model.ib_instr_id = result_ib_instr_id.text
            if result_status is not None and result_status.text is not None:
                result_model.status = result_status.text
            if result_code is not None and result_code.text is not None:
                result_model.code = result_code.text
            if result_description is not None and result_description.text is not None:
                result_model.description = result_description.text
            result_model.save()

    def _handle_instruction_name(self, funding_request: FundingRequest, details_root: ET.Element):
        status = details_root.find('./fbrs:get_instructions_result/fbrs:status', self.ns)
        ib_instr_id = details_root.find('./fbrs:get_instructions_result/fbrs:ib_instr_id', self.ns)
        client_ib_acct_id = details_root.find('./fbrs:get_instructions_result/fbrs:client_ib_acct_id', self.ns)
        code = details_root.find('./fbrs:get_instructions_result/fbrs:code', self.ns)
        description = details_root.find('./fbrs:get_instructions_result/fbrs:description', self.ns)
        instruction_details = details_root.find('./fbrs:get_instructions_result/fbrs:instruction_details', self.ns)
        if code is not None and description is not None:
            funding_request_status = funding_request.status
            funding_request_status.error_code = code.text
            funding_request_status.error_message = description.text
            funding_request_status.save()
            data = {
                "ib_instr_id": ib_instr_id.text,
                "code": code.text,
                "description": description.text
            }
            funding_request.response_data = data
            funding_request.save()
        if instruction_details is not None:
            method = details_root.find('./fbrs:get_instructions_result/fbrs:method', self.ns)
            instruction_name = instruction_details.find('./fbrs:instruction_name', self.ns)
            type_node = instruction_details.find('./fbrs:type', self.ns)
            currency = instruction_details.find('./fbrs:currency', self.ns)
            data = {
                "status": status.text,
                "ib_instr_id": ib_instr_id.text,
                "client_ib_acct_id": client_ib_acct_id.text,
                "method": method.text,
                "instruction_details": {
                    "instruction_name": instruction_name.text,
                    "type": type_node.text,
                    "currency": currency.text
                }
            }
            funding_request.response_data = data
            funding_request.save()

    def _handle_get_status(self, funding_request: FundingRequest, details_root: ET.Element):
        if funding_request.method == 'deposit_funds':
            self._handle_deposit_funds_response(funding_request, details_root)
        return funding_request
