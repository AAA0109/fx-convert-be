import xml.etree.ElementTree as ET
from abc import ABC
from typing import OrderedDict, Tuple, Optional

from hdlib.DateTime.Date import Date

from main.apps.account.models import User
from main.apps.ibkr.services.eca.connector import IBECAConnector


class IBECAService(ABC):
    _connector = None

    @property
    def connector(self):
        if self._connector is None:
            self._connector = IBECAConnector()
        return self._connector

    def get_tasks(self, task: str, broker_account_id: str, start_date: Optional[Date.date],
                  end_date: Optional[Date.date], form_number: Optional[int]):
        status_code = None
        response = None
        if task == 'pending':
            status_code, response = self.connector.get_pending_tasks([broker_account_id],
                                                                     start_date, end_date, form_number)
        if task == 'registration':
            status_code, response = self.connector.get_registration_tasks([broker_account_id],
                                                                          start_date, end_date, form_number)
        if status_code == 200:
            return response['result']

    def get_sso_create_url(self, credential, ip) -> str:
        status_code, response = self.connector.sso_create(credential, ip)
        if status_code == 200:
            if response['RESULT']:
                url = self.connector.decode_and_decrypt_data(response['SIGNED_URL'])
                return url

    def get_account_status(self, account_ids: Optional[list] = None, start_date: Optional[Date] = None,
                           end_date: Optional[Date] = None, status: Optional[str] = None):
        status_code, response = self.connector.get_account_status(account_ids, start_date, end_date, status)
        if status_code == 200:
            return response

    def healthcheck(self) -> bool:
        status_code, response = self.connector.healthcheck()
        if status_code == 200:
            if response['status'] == 'alive':
                return True
        return False

    def create_application_for_user(self, user: User, data: OrderedDict) -> Tuple:
        now = Date.now()
        now_str = Date(now.year, now.month, now.day, now.hour, now.minute, now.second).to_str('%Y-%m-%d-%H-%M-%S')
        xml = self.get_application_xml_for_user(user, data)
        payload = self.connector.create_request_payload_from_xml(xml=xml, filename=f"{user.company.pk}_{now_str}",
                                                                 zip_xml=True)
        response_code, response_data = self.connector.create(payload=payload)
        if response_code == 200:
            return_data = {}
            errors = []
            if response_data['isProcessed']:
                encoded_message = response_data['fileData']['data']
                filename = response_data['fileData']['name']
                response_xml = self.connector.decode_and_decrypt_xml_response(encoded_message, filename)
                response_tree = ET.ElementTree(ET.fromstring(response_xml))
                response_root = response_tree.getroot()
                response_application = response_root.find("./Applications/Application")
                response_status = response_application.attrib['Status']
                if response_status == 'Error':
                    for error in response_root.findall("./Applications/Application/Errors/Error"):
                        errors.append(error.text)
                        return response_status, errors
                if response_status == 'Success':
                    response_user = response_application.find("./Users/User")
                    response_account = response_application.find('./Accounts/Account')
                    response_entity = response_application.find('./Entities/Entity')
                    return_data['external_id'] = response_application.attrib.get('External_ID')
                    return_data['user'] = response_user.text
                    return_data['user_id'] = response_user.attrib.get('user_id')
                    return_data['account'] = response_account.text
                    return_data['entity'] = response_entity.text
                return response_status, return_data
            else:
                return response_data['fileData']['data'], return_data

    def get_application_xml_for_user(self, user: User, data: OrderedDict) -> str:
        applications = ET.Element('Applications')
        applications.set('xmlns', 'http://www.interactivebrokers.com/schemas/IBCust_import')
        for _application in data['application']:
            application = ET.SubElement(applications, 'Application')
            for _customer in _application['customers']:
                customer = ET.SubElement(application, 'Customer')
                customer.set('email', _customer['email'])
                customer.set('external_id', _customer['external_id'])
                customer.set('md_status_nonpro', 'true' if _customer['md_status_nonpro'] else 'false')
                customer.set('prefix', _customer['prefix'])
                customer.set('type', _customer['type'])

                _organization = _customer['organization']
                organization = ET.SubElement(customer, 'Organization')
                organization.set('us_tax_purpose_type', _organization['us_tax_purpose_type'])
                organization.set('type', _organization['type'])

                _organization_identification = _organization['identification']
                organization_identification = ET.SubElement(organization, 'Identification')
                organization_identification.set('formation_country', _organization_identification['formation_country'])
                organization_identification.set('identification_country',
                                                _organization_identification['identification_country'])
                organization_identification.set('identification', _organization_identification['identification'])
                organization_identification.set('name', _organization_identification['name'])
                organization_identification.set('same_mail_address', 'true' if _organization_identification[
                    'same_mail_address'] else 'false')

                _place_of_business = _organization_identification['place_of_business']
                place_of_business = ET.SubElement(organization_identification, 'PlaceOfBusiness')
                place_of_business.set('city', _place_of_business['city'])
                place_of_business.set('country', _place_of_business['country'])
                place_of_business.set('postal_code', _place_of_business['postal_code'])
                place_of_business.set('state', _place_of_business['state'])
                place_of_business.set('street_1', _place_of_business['street_1'])
                if ('street_2' in _place_of_business) and _place_of_business['street_2']:
                    place_of_business.set('street_2', _place_of_business['street_2'])

                if not _organization_identification['same_mail_address']:
                    _mailing_address = _organization_identification['mailing_address']
                    mailing_address = ET.SubElement(organization_identification, 'MailingAddress')
                    mailing_address.set('country', _mailing_address['country'])
                    mailing_address.set('state', _mailing_address['state'])
                    mailing_address.set('city', _mailing_address['city'])
                    mailing_address.set('postal_code', _mailing_address['postal_code'])
                    mailing_address.set('street_1', _mailing_address['street_1'])
                    if ('street_2' in _mailing_address) and _mailing_address['street_2']:
                        mailing_address.set('street_2', _mailing_address['street_2'])

                organization_tax_residencies = ET.SubElement(organization, 'TaxResidencies')
                for _organization_tax_residency in _organization['tax_residencies']:
                    organization_tax_residency = ET.SubElement(organization_tax_residencies, 'TaxResidency')
                    organization_tax_residency.set('TIN', _organization_tax_residency['tin'])
                    organization_tax_residency.set('country', _organization_tax_residency['country'])

                _associated_entities = _organization['associated_entities']
                associated_entities = ET.SubElement(organization, 'AssociatedEntities')

                for _associated_individual in _associated_entities['associated_individual']:
                    associated_individual = ET.SubElement(associated_entities, 'AssociatedIndividual')
                    associated_individual.set('AuthorizedPerson',
                                              'true' if _associated_individual['authorized_person'] else 'false')
                    associated_individual.set('external_id', _associated_individual['external_id'])

                    _name = _associated_individual['name']
                    name = ET.SubElement(associated_individual, 'Name')
                    name.set('first', _name['first'])
                    if 'middle' in _name and _name['middle']:
                        name.set('middle', _name['middle'])
                    name.set('last', _name['last'])
                    name.set('salutation', _name['salutation'])

                    dob = ET.SubElement(associated_individual, 'DOB')
                    dob.text = _associated_individual['dob'].strftime("%Y-%m-%d")

                    _residence = _associated_individual['residence']
                    residence = ET.SubElement(associated_individual, 'Residence')
                    residence.set('city', _residence['city'])
                    residence.set('country', _residence['country'])
                    residence.set('postal_code', _residence['postal_code'])
                    residence.set('state', _residence['state'])
                    residence.set('street_1', _residence['street_1'])
                    if ('street_2' in _residence) and _residence['street_2']:
                        residence.set('street_2', _residence['street_2'])

                    if 'mailing_address' in _associated_individual:
                        _mailing_address = _associated_individual['mailing_address']
                        mailing_address = ET.SubElement(associated_individual, 'MailingAddress')
                        mailing_address.set('country', _mailing_address['country'])
                        mailing_address.set('state', _mailing_address['state'])
                        mailing_address.set('city', _mailing_address['city'])
                        mailing_address.set('postal_code', _mailing_address['postal_code'])
                        mailing_address.set('street_1', _mailing_address['street_1'])
                        if ('street_2' in _mailing_address) and _mailing_address['street_2']:
                            mailing_address.set('street_2', _mailing_address['street_2'])

                    email = ET.SubElement(associated_individual, 'Email')
                    email.set('email', _associated_individual['email'])

                    _identification = _associated_individual['identification']
                    identification = ET.SubElement(associated_individual, 'Identification')
                    identification.set('IssuingCountry', _identification['issuing_country'])
                    identification.set('LegalResidenceCountry', _identification['legal_residence_country'])
                    identification.set('LegalResidenceState', _identification['legal_residence_state'])
                    identification.set('SSN', _identification['ssn'])
                    identification.set('citizenship', _identification['citizenship'])

                    tax_residencies = ET.SubElement(associated_individual, 'TaxResidencies')
                    for _tax_residency in _associated_individual['tax_residencies']:
                        tax_residency = ET.SubElement(tax_residencies, 'TaxResidency')
                        tax_residency.set('TIN', _tax_residency['tin'])
                        tax_residency.set('TINType', _tax_residency['tin_type'])
                        tax_residency.set('country', _tax_residency['country'])

                    _title = _associated_individual['title']
                    title = ET.SubElement(associated_individual, 'Title')
                    title.set('code', _title['code'])

            accounts = ET.SubElement(application, 'Accounts')
            for _account in _application['accounts']:
                account = ET.SubElement(accounts, 'Account')
                account.set('base_currency', _account['base_currency'])
                account.set('external_id', _account['external_id'])
                account.set('margin', _account['margin'])
                account.set('multicurrency', 'true' if _account['multicurrency'] else 'no')
                trading_permissions = ET.SubElement(account, 'TradingPermissions')
                trading_permission = ET.SubElement(trading_permissions, 'TradingPermission')
                trading_permission.set('exchange_group', 'US-Sec')
                _fees = _account['fees']
                fees = ET.SubElement(account, 'Fees')
                fees.set('template_name', _fees['template_name'])

            users = ET.SubElement(application, 'Users')
            for _user in _application['users']:
                user = ET.SubElement(users, 'User')
                user.set('external_individual_id', _user['external_individual_id'])
                user.set('external_user_id', _user['external_user_id'])
                user.set('prefix', _user['prefix'])

        return ET.tostring(applications, encoding="unicode")

    def _convert_company_name_to_prefix(self, name: str) -> str:
        if len(name) < 5:
            raise ValueError("Company name does not have enough characters")
        return ''.join(e for e in name if e.isalnum()).lower()[0:5]
