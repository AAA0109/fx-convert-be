import os
import unittest
import xml.etree.ElementTree as ET

from django.conf import settings
from django.test import TestCase

import main.apps.ibkr as ibkr
from main.apps.ibkr.services.eca.connector import IBECAConnector


class IBECATestCase(TestCase):
    APP_PATH = str(settings.BASE_DIR.parent)
    IBKR_APP_PATH = os.path.dirname(ibkr.__file__)
    IBKR_FIXTURES_TEST_PATH = f"{IBKR_APP_PATH}/fixtures/tests"
    STORAGE_PATH = f"{APP_PATH}/storage"
    DAM_APPLICATIONS_PATH = f"{STORAGE_PATH}/dam/applications"
    DAM_APPLICATIONS_XML_PATH = f"{DAM_APPLICATIONS_PATH}/xml"
    DAM_APPLICATIONS_ZIP_PATH = f"{DAM_APPLICATIONS_PATH}/zip"
    DAM_APPLICATIONS_XML_FILE_PATH = f"{DAM_APPLICATIONS_XML_PATH}/test.xml"
    DAM_APPLICATIONS_ZIP_FILE_PATH = f"{DAM_APPLICATIONS_ZIP_PATH}/test.zip"
    DAM_APPLICATIONS_ENCRYPTED_ZIP_FILE_PATH = f"{DAM_APPLICATIONS_ZIP_PATH}/test_encrypted.zip"

    def setUp(self) -> None:
        self.ib_dam_connector = IBECAConnector()

    @unittest.skipIf(not settings.IB_RUN_TESTS, "Only run if IB_RUN_TESTS is set to True")
    def test_create_application_success(self):
        success_xml_path = f"{self.IBKR_FIXTURES_TEST_PATH}/eca/create/success.xml"
        f = open(success_xml_path, 'r')
        response_xml = f.read()
        response_tree = ET.ElementTree(ET.fromstring(response_xml))
        response_root = response_tree.getroot()
        response_application = response_root.find("./Applications/Application")
        response_status = response_application.attrib.get('Status')
        response_user = response_application.find("./Users/User")
        response_account = response_application.find('./Accounts/Account')
        response_entity = response_application.find('./Entities/Entity')
        self.assertEqual(response_application.attrib.get('External_ID'), 'PangeaJay')
        self.assertEqual(response_status, 'Success')
        self.assertEqual(response_user.text, 'pangea659')
        self.assertEqual(response_account.text, 'U91035882')
        self.assertEqual(response_entity.text, '163906919')

    # Integration Tests Below #
    @unittest.skipIf(not settings.IB_RUN_TESTS, "Only run if IB_RUN_TESTS is set to True")
    def test_create(self):
        # create sample application xml file
        xml = self._get_sample_application_xml(email='jamison@pangea.io', ssn="111223338", external_id="PangeaJamison")
        payload = self.ib_dam_connector.create_request_payload_from_xml(xml=xml, filename="test", zip_xml=True)
        response_code, response_data = self.ib_dam_connector.create(payload=payload)
        if response_code == 200:
            encoded_message = response_data['fileData']['data']
            filename = response_data['fileData']['name']
            response_xml = self.ib_dam_connector.decode_and_decrypt_xml_response(encoded_message, filename)
            response_tree = ET.ElementTree(ET.fromstring(response_xml))
            response_root = response_tree.getroot()
            response_application = response_root.find("./Applications/Application")
            response_status = response_application.attrib['Status']
            self.assertIn(response_status, ['Success', 'Already processed'])

    @unittest.skipIf(not settings.IB_RUN_TESTS, "Only run if IB_RUN_TESTS is set to True")
    def test_sso_create(self):
        credential = "teste6356"
        ip = "68.104.18.101"
        response_code, response_data = self.ib_dam_connector.sso_create(credential, ip)
        if response_code == 200:
            url = self.ib_dam_connector.decode_and_decrypt_data(response_data['SIGNED_URL'])
            print("IB DAM SSO URL: " + url.decode("UTF-8"))
            self.assertTrue(response_data['RESULT'])

    def _get_sample_application_xml(self, email, ssn, external_id):
        applications = ET.Element('Applications')
        applications.set('xmlns', 'http://www.interactivebrokers.com/schemas/IBCust_import')
        application = ET.SubElement(applications, 'Application')
        customer = ET.SubElement(application, 'Customer')
        customer.set('email', email)
        customer.set('external_id', external_id)
        customer.set('md_status_nonpro', 'false')
        customer.set('prefix', 'teste')
        customer.set('type', 'ORG')
        organization = ET.SubElement(customer, 'Organization')
        organization.set('us_tax_purpose_type', 'C')
        organization.set('type', 'PARTNERSHIP')
        organization_identification = ET.SubElement(organization, 'Identification')
        organization_identification.set('formation_country', 'USA')
        organization_identification.set('identification', '11122333')
        organization_identification.set('identification_country', 'USA')
        organization_identification.set('name', 'Test Org')
        organization_identification.set('same_mail_address', 'true')
        place_of_business = ET.SubElement(organization_identification, 'PlaceOfBusiness')
        place_of_business.set('city', 'Greewnich City')
        place_of_business.set('country', 'USA')
        place_of_business.set('postal_code', '06905')
        place_of_business.set('state', 'CT')
        place_of_business.set('street_1', 'Pickwick Plaza')
        organization_tax_residencies = ET.SubElement(organization, 'TaxResidencies')
        organization_tax_residency = ET.SubElement(organization_tax_residencies, 'TaxResidency')
        organization_tax_residency.set('TIN', '11122333')
        organization_tax_residency.set('country', 'USA')
        associated_entities = ET.SubElement(organization, 'AssociatedEntities')
        associated_individual = ET.SubElement(associated_entities, 'AssociatedIndividual')
        associated_individual.set('AuthorizedPerson', 'true')
        associated_individual.set('external_id', external_id)
        associated_individual_name = ET.SubElement(associated_individual, 'Name')
        associated_individual_name.set('first', 'Tester')
        associated_individual_name.set('last', 'Test')
        associated_individual_name.set('salutation', 'Mrs.')
        associated_individual_dob = ET.SubElement(associated_individual, 'DOB')
        associated_individual_dob.text = '1990-05-21'
        associated_individual_residence = ET.SubElement(associated_individual, 'Residence')
        associated_individual_residence.set('city', 'Greewnich City')
        associated_individual_residence.set('country', 'USA')
        associated_individual_residence.set('postal_code', '06905')
        associated_individual_residence.set('state', 'CT')
        associated_individual_residence.set('street_1', 'Pickwick Plaza')
        associated_individual_email = ET.SubElement(associated_individual, 'Email')
        associated_individual_email.set('email', email)
        associated_individual_identification = ET.SubElement(associated_individual, 'Identification')
        associated_individual_identification.set('IssuingCountry', 'USA')
        associated_individual_identification.set('SSN', ssn)
        associated_individual_identification.set('citizenship', 'USA')
        associated_individual_tax_residencies = ET.SubElement(associated_individual, 'TaxResidencies')
        associated_individual_tax_residency = ET.SubElement(associated_individual_tax_residencies, 'TaxResidency')
        associated_individual_tax_residency.set('TIN', ssn)
        associated_individual_tax_residency.set('TINType', 'SSN')
        associated_individual_tax_residency.set('country', 'USA')
        associated_individual_title = ET.SubElement(associated_individual, 'Title')
        associated_individual_title.set('code', 'SECRETARY')
        accounts = ET.SubElement(application, 'Accounts')
        account = ET.SubElement(accounts, 'Account')
        account.set('base_currency', 'USD')
        account.set('external_id', external_id)
        account.set('margin', 'Cash')
        account.set('multicurrency', 'true')
        trading_permissions = ET.SubElement(account, 'TradingPermissions')
        trading_permission = ET.SubElement(trading_permissions, 'TradingPermission')
        trading_permission.set('exchange_group', 'US-Sec')
        fees = ET.SubElement(account, 'Fees')
        fees.set('template_name', 'test123')
        users = ET.SubElement(application, 'Users')
        user = ET.SubElement(users, 'User')
        user.set('external_individual_id', external_id)
        user.set('external_user_id', external_id)
        user.set('prefix', 'teste')
        return ET.tostring(applications, encoding="unicode")
