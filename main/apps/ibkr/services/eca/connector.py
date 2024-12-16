import os
from abc import ABC
from typing import Tuple, Optional

import requests
from django.conf import settings

from zipfile import ZipFile
import gnupg
import base64
import json
import logging

from hdlib.DateTime.Date import Date

from main.apps.core.services.http_request import HTTPRequestService

logger = logging.getLogger(__name__)


class IBECAConnector(HTTPRequestService):
    api_url: str = settings.IB_DAM_URL
    csid: str = settings.IB_DAM_CSID
    APP_PATH = str(settings.BASE_DIR.parent)
    STORAGE_PATH = f"{APP_PATH}/storage"
    DAM_APPLICATIONS_PATH = f"{STORAGE_PATH}/dam/applications"
    DAM_APPLICATIONS_XML_REQUEST_PATH = f"{DAM_APPLICATIONS_PATH}/xml/request"
    DAM_APPLICATIONS_XML_RESPONSE_PATH = f"{DAM_APPLICATIONS_PATH}/xml/response"
    DAM_APPLICATIONS_ZIP_REQUEST_PATH = f"{DAM_APPLICATIONS_PATH}/zip/request"

    def __init__(self):
        try:
            self.gpg = gnupg.GPG(gnupghome=settings.GPG_HOME_DIR)
        except (OSError, FileNotFoundError) as e:
            logger.error(e)

    def create(self, payload: str) -> Tuple:
        url = f"{self.api_url}/ws/eca/create"
        data = {
            "CSID": self.csid,
            "payload": payload
        }
        response = self.make_request('post', url, data)
        return response.status_code, response.json()

    def sso_create(self, credential: str, ip: str):
        url = f"{self.api_url}/ws/sso/create"
        data = {
            "CREDENTIAL": credential,
            "IP": ip,
            "CONTEXT": "AM.LOGIN"
        }
        payload_json = json.dumps(data)
        encrypted_payload = self.encrypt_and_encode_payload(payload_json)
        request_payload = {
            "CSID": self.csid,
            "payload": encrypted_payload
        }
        response = self.make_request('post', url, request_payload)
        return response.status_code, response.json()

    def healthcheck(self):
        url = f"{self.api_url}/ws/eca/healthcheck"
        data = {
            "CSID": self.csid
        }
        response = self.make_request('post', url, data)
        return response.status_code, response.json()

    def get_account_status(self, account_ids: Optional[list] = None, start_date: Optional[Date] = None,
                           end_date: Optional[Date] = None, status: Optional[str] = None) -> Tuple[int, dict]:
        """
        Get Account Status

        @param account_ids: Optional - if querying by account ID or custom group of accounts.
        @param start_date: Optional - if querying for accounts created within specific date range.
        @param end_date: If start_date is provided, end_date is mandatory.
        @param status: Optional - if querying for accounts based on status.
        A= Abandoned (i.e. application was deleted)

        N= New Account / Not Yet Open - No Funding Details have been provided.

        O= Open (Considered active accounts)

        C= Closed (considered accounts that were once active OR open accounts that were and then closed.)

        P= Pending - Funding instructions have been provided.

        R= Rejected (meaning account was never approved/opened - rejected by Compliance)

        @return:
        {
          "timestamp": "<timestamp>",
          "status" : [{
            "accountId" : "<ID1>",
            "isError" : false,
            "description" : "<Status Description>",
            "status" : "<Status Code>"
          }, {
            "accountId" : "ID2",
            "isError" : true,
            "error" : "<Error Description>."
          }]
        }
        """
        url = f"{self.api_url}/ws/eca/getAccountStatus"
        data = {
            "CSID": self.csid
        }
        data = self._validate_account_ids_and_date(data, account_ids, start_date, end_date)

        if status is not None:
            data['status'] = status

        response = self.make_request('post', url, data)

        return response.status_code, response.json()

    def get_pending_tasks(self, account_ids: Optional[list] = None, start_date: Optional[Date] = None,
                          end_date: Optional[Date] = None, form_number: Optional[str] = None) -> Tuple[int, dict]:
        """

        @param account_ids: Optional - if querying by account ID or custom group of accounts.
        @param start_date: Optional - if querying for accounts created within specific date range.
        @param end_date: If startDate is provided, endDate is mandatory.
        @param form_number: Optional - used to filter list of accounts pending due to specific task or form_no.
        @return:
        {
            "result" : [
                {
                  "pendingTasks" : [
                  {
                     "isRequiredForTrading" : "<true|false>",
                     "isOnlineTask" : "<true|false>",
                     "formNumber" : "<form_number>",
                     "formName" : "<form_name>",
                     "action" : "<required_action>",
                     "isRequiredForApproval" : "<true|false>",
                     "taskNumber" : "<task_number"
                  }
                  ],
                  "isError" : "<true|false>",
                  "isPendingTaskPresent" : "<true|false>,
                  "acctId" : "<ID1>",
                  "error" : "<error>"
                }
            ],
            "timestamp" : "<time_stamp>"
        }
        """
        return self._get_tasks('pending', account_ids, start_date, end_date, form_number)

    def get_registration_tasks(self, account_ids: Optional[list] = None, start_date: Optional[Date] = None,
                               end_date: Optional[Date] = None, form_number: Optional[str] = None) -> Tuple[int, dict]:
        """

        @param account_ids:
        @param start_date:
        @param end_date:
        @param form_number:
        @return:
        {
        "result" :
            [
                {
                    [
                        {
                            "isRegistrationTasksPresent" : "<true|false>",
                            "isRequiredForTrading" : "<true|false>",
                            "isOnlineTask" : "<true|false>",
                            "formNumber" : "<form_number>",
                            "formName" : "<form_name>",
                            "action" : "<required_action>",
                            "isRequiredForApproval" : "<true|false>",
                            "taskNumber" : "<task_number"
                        }
                    ],
                    "isError" : "<true|false>",
                    "isPendingTaskPresent" : "<true|false>,
                    "acctId" : "<ID1>",
                    "error" : "<error>"
                }
            ],
            "timestamp" : "<time_stamp>"
        }
        """
        return self._get_tasks('registration', account_ids, start_date, end_date, form_number)

    def _get_tasks(self, type: str, account_ids: Optional[list] = None, start_date: Optional[Date] = None,
                   end_date: Optional[Date] = None, form_number: Optional[str] = None) -> Tuple[int, dict]:
        url = None
        if type == 'pending':
            url = f"{self.api_url}/ws/eca/getPendingTasks"
        if type == 'registration':
            url = f"{self.api_url}/ws/eca/getRegistrationTasks"
        if url is None:
            raise ValueError("unable to get url for the task type")

        data = {
            "CSID": self.csid
        }
        data = self._validate_account_ids_and_date(data, account_ids, start_date, end_date)

        if form_number is not None:
            data['formNumber'] = form_number

        response = self.make_request('post', url, data)

        return response.status_code, response.json()

    def make_request(self, method: str = 'post', url: str = '', data: dict = {}, headers=None):
        logger.debug(f"IBKR DAM making request: {url} {data}")
        response = super().make_request(method=method, url=url, data=data)
        logger.debug(f"IBKR DAM Response: {response.status_code} {response.content.decode('utf8')}")
        return response

    @staticmethod
    def _validate_account_ids_and_date(data: dict, account_ids, start_date, end_date):
        if account_ids is not None:
            data['accountIds'] = account_ids
        if start_date is not None:
            data['startDate'] = start_date.to_str('%Y-%m-%d')
            if end_date is None:
                raise ValueError("end_date is required if start_date is not None")
            data['endDate'] = end_date.to_str('%Y-%m-%d')
        return data

    def encrypt_and_encode_payload(self, data: str):
        crypt = self.gpg.encrypt(
            data=data,
            recipients=settings.GPG_RECIPIENT,
            sign=settings.GPG_SIGNER,
            passphrase=settings.GPG_PASSPHRASE,
            armor=False
        )
        if crypt.ok:
            return base64.b64encode(crypt.data).decode('ascii')
        else:
            raise RuntimeError(f"{crypt.status} {crypt.stderr}")

    def decode_and_decrypt_data(self, data):
        decoded_data = base64.b64decode(data)
        crypt = self.gpg.decrypt(decoded_data)
        if crypt.ok:
            return crypt.data
        else:
            raise RuntimeError(f"{crypt.status} {crypt.stderr}")

    def decode_btye_str(self, data):
        data = data.decode("utf-8")
        logger.debug(f"Decoded response: {data}")
        return data

    def create_request_payload_from_xml(self, xml: str, filename: str, zip_xml=False):
        xml_file_path = f"{self.DAM_APPLICATIONS_XML_REQUEST_PATH}/{filename}.xml"
        zip_file_path = f"{self.DAM_APPLICATIONS_ZIP_REQUEST_PATH}/{filename}.zip"
        encrypted_zip_file_path = f"{self.DAM_APPLICATIONS_ZIP_REQUEST_PATH}/encrypted_{filename}.zip"
        xml_file = open(xml_file_path, "w")
        try:
            # TODO: encrypt before saving
            xml_file.write(xml)
        finally:
            xml_file.close()
        if zip_xml:
            ZipFile(zip_file_path, mode="w").write(xml_file_path, f"{filename}.xml")
            stream = open(zip_file_path, "rb")
        else:
            stream = open(xml_file_path, "r")
        crypt = self.gpg.encrypt_file(
            stream,
            recipients=settings.GPG_RECIPIENT,
            sign=settings.GPG_SIGNER,
            passphrase=settings.GPG_PASSPHRASE,
            output=encrypted_zip_file_path,
            armor=False
        )
        if crypt.ok:
            with open(encrypted_zip_file_path, 'rb') as f:
                b = f.read()
                b64data = base64.b64encode(b).decode('ascii')
                if not os.environ.get('DJANGO_SETTINGS_MODULE') == 'main.settings.local':
                    os.remove(xml_file_path)
                    os.remove(zip_file_path)
                return b64data
        else:
            raise RuntimeError(f"{crypt.status} {crypt.stderr}")

    def decode_and_decrypt_xml_response(self, encoded_message, filename):
        decrypted_xml_file_path = f"{self.DAM_APPLICATIONS_XML_RESPONSE_PATH}/{filename}"
        decoded_message = base64.b64decode(encoded_message)
        crypt = self.gpg.decrypt(decoded_message, output=decrypted_xml_file_path)
        if crypt.ok:
            f = open(decrypted_xml_file_path, 'r')
            return f.read()
        else:
            raise RuntimeError(f"{crypt.status} {crypt.stderr}")
