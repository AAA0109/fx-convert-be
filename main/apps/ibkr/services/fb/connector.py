import xml.etree.ElementTree as ET
from typing import Tuple, OrderedDict, Iterable

from hdlib.DateTime.Date import Date

from main.apps.ibkr.services.eca.connector import IBECAConnector


class IBFBConnector(IBECAConnector):
    """
    Create a new request, see https://guides.interactivebrokers.com/damfb/Content/Available%20Functions.htm for available functions

    :param str request: base64-encoded, PGP encrypted and signed XML payload
    """

    def new_request(self, request: str) -> Tuple:
        url = f"{self.api_url}/ws/fb/new-request"
        data = {
            "CSID": self.csid,
            "request": request
        }
        response = self.make_request('post', url, data)
        return self._handle_response(response)

    def deposit_funds(self, account_number: str, id: int, data: OrderedDict) -> Tuple:
        xml = self._create_deposit_funds_xml(account_number, id, data)
        return self._send_xml_request(xml)

    def withdraw_funds(self, account_number, id: int, data: OrderedDict):
        xml = self._create_withdraw_funds_xml(account_number, id, data)
        return self._send_xml_request(xml)

    def get_instruction_name(self, account_number: str, id: int, method: str):
        xml = self._create_get_instruction_name_xml(account_number, id, method)
        return self._send_xml_request(xml)

    def predefined_destination_instruction(self, account_number: str, id: int, data: OrderedDict):
        xml = self._create_predefined_destination_instruction_xml(account_number, id, data)
        return self._send_xml_request(xml)

    def get_status(self, instruction_set_id: int):
        url = f"{self.api_url}/ws/fb/get-status"
        data = {
            "CSID": self.csid,
            "instruction_set_id": self.encrypt_and_encode_payload(str(instruction_set_id))
        }
        response = self.make_request('post', url, data)
        return self._handle_response(response)

    def get_updated_upload_ids(self, date: Date) -> Iterable[int]:
        url = f"{self.api_url}/ws/fb/get_updated_upload_ids"
        data = {
            "CSID": self.csid,
            "since_yyyy-mm-dd": self.encrypt_and_encode_payload(date.to_str("%Y-%m-%d"))
        }
        response = self.make_request('post', url, data)
        return self._handle_response(response)

    def _send_xml_request(self, xml: str):
        payload = self.encrypt_and_encode_payload(xml)
        status_code, json = self.new_request(payload)
        return status_code, json

    def _create_deposit_funds_xml(self, account_number: str, id: int,
                                  data: OrderedDict):
        instruction_set = self._get_instruction_set_xml_node(id, 1)
        deposit_funds = ET.SubElement(instruction_set, 'deposit_funds')
        deposit_funds.set('id', str(id))
        account_number_node = ET.SubElement(deposit_funds, 'account_number')
        account_number_node.text = account_number
        amount = ET.SubElement(deposit_funds, 'amount')
        amount.text = str(data['amount'])
        currency = ET.SubElement(deposit_funds, 'currency')
        currency.text = data['currency']
        method = ET.SubElement(deposit_funds, 'method')
        method.text = data['method']
        if 'saved_instruction_name' in data:
            saved_instruction_name = ET.SubElement(deposit_funds, 'saved_instruction_name')
            saved_instruction_name.text = data['saved_instruction_name']
        return ET.tostring(instruction_set, encoding='unicode')

    def _create_withdraw_funds_xml(self, account_number: str, id: int,
                                   data: OrderedDict):
        instruction_set = self._get_instruction_set_xml_node(id, 1.2)
        withdraw_funds = ET.SubElement(instruction_set, 'withdraw_funds')
        withdraw_funds.set('id', str(id))
        account_number_node = ET.SubElement(instruction_set, 'account_number')
        account_number_node.text = account_number
        amount = ET.SubElement(instruction_set, 'amount')
        amount.text = data.get('amount')
        method = ET.SubElement(instruction_set, 'method')
        method.text = data.get('method')
        date_time_to_occur = ET.SubElement(instruction_set, 'date_time_to_occur')
        date_time_to_occur.text = data.get('date_time_to_occur')

        return ET.tostring(instruction_set, encoding="unicode")

    def _create_get_instruction_name_xml(self, account_number: str, id: int, method: str):
        instruction_set = self._get_instruction_set_xml_node(id, 1.2)
        get_instruction_name = ET.SubElement(instruction_set, 'get_instruction_name')
        get_instruction_name.set('id', str(id))
        account_number_node = ET.SubElement(get_instruction_name, 'account_number')
        account_number_node.text = account_number
        method_node = ET.SubElement(get_instruction_name, 'method')
        method_node.text = method
        return ET.tostring(instruction_set, encoding='unicode')

    def _create_predefined_destination_instruction_xml(self, account_number: str, id: int, data: OrderedDict):
        instruction_set = self._get_instruction_set_xml_node(id, 1.1)
        predefined_destination_instruction = ET.SubElement(instruction_set, 'predefined_destination_instruction')
        predefined_destination_instruction.set('id', str(id))
        instruction_name = ET.SubElement(predefined_destination_instruction, 'instruction_name')
        instruction_name.text = data.get('instruction_name')
        instruction_type = ET.SubElement(predefined_destination_instruction, 'instruction_type')
        instruction_type.text = data.get('instruction_type')
        financial_institution_node = ET.SubElement(predefined_destination_instruction, 'financial_institution')
        financial_institution = data.get('financial_institution')
        financial_institution_name = ET.SubElement(financial_institution_node, 'name')
        financial_institution_name.text = financial_institution.get('name')
        financial_institution_identifier = ET.SubElement(financial_institution_node, 'identifier')
        financial_institution_identifier.text = financial_institution.get('identifier')
        financial_institution_identifier_type = ET.SubElement(financial_institution_node, 'identifier_type')
        financial_institution_identifier_type.text = financial_institution.get('identifier_type')
        currency = ET.SubElement(predefined_destination_instruction, 'currency')
        currency.text = data.get('currency')
        ib_client_acct_id = ET.SubElement(predefined_destination_instruction, 'ib_client_acct_id')
        ib_client_acct_id.text = account_number
        return ET.tostring(instruction_set, encoding='unicode')

    @staticmethod
    def _get_instruction_set_xml_node(id: int, version: float = 1) -> ET.Element:
        instruction_set = ET.Element('instruction_set')
        instruction_set.set('xmlns', 'http://www.interactivebrokers.com/fbfb_instruction_set')
        instruction_set.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        instruction_set.set('xsi:schemaLocation',
                            'http://www.interactivebrokers.com/fbfb_instruction_set fbfb_instruction_set.xsd')
        instruction_set.set('version', str(version))
        instruction_set.set('id', str(id))

        now = Date.now()
        instruction_set.set('creation_date', Date(now.year, now.month, now.day).to_str('%Y-%m-%d'))

        return instruction_set

    @staticmethod
    def _handle_response(response) -> Tuple:
        if response.status_code == 200:
            json = response.json()
            return response.status_code, json
        if response.status_code == 500:
            raise RuntimeError("500 Error from IB")
