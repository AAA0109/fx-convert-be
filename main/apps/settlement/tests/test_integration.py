import json
import logging
from random import randint
from unittest import skipIf

import jsonschema
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from main.apps.account.models import Company
from main.apps.broker.models import Broker, BrokerProviderOption, BrokerCompany
from main.apps.corpay.models import CorpaySettings
from main.apps.currency.models import Currency
from main.apps.currency.models.fxpair import FxPair
from main.apps.monex.models import MonexCompanySettings
from main.apps.nium.models import NiumSettings
from main.apps.oems.models.cny import CnyExecution
from main.apps.settlement.models import Beneficiary
from main.apps.settlement.services.beneficiary import BeneficiaryFieldConfigService, BeneficiaryFieldMappingService, \
    BeneficiaryValueMappingService

logger = logging.getLogger(__name__)


@skipIf(settings.APP_ENVIRONMENT != 'local', "This test is only for the dev environment")
class BeneficiaryViewSetIntegrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.broker_nium = Broker.objects.create(
            name="Nium",
            broker_provider=BrokerProviderOption.NIUM
        )
        self.broker_corpay = Broker.objects.create(
            name="Corpay",
            broker_provider=BrokerProviderOption.CORPAY
        )
        self.broker_monex = Broker.objects.create(
            name="Monex",
            broker_provider=BrokerProviderOption.MONEX
        )
        self.currencies = {
            'usd': Currency.objects.create(mnemonic='USD', name="US Dollar"),
            'brl': Currency.objects.create(mnemonic='BRL', name="Brazilian Real"),
            'npr': Currency.objects.create(mnemonic='NPR', name="Nepalese Rupee"),
            'cop': Currency.objects.create(mnemonic='COP', name="Colombian Peso"),
            'clp': Currency.objects.create(mnemonic='CLP', name="Chilian Peso"),
            'idr': Currency.objects.create(mnemonic='IDR', name="Indonesian Rupiah"),
            'php': Currency.objects.create(mnemonic="PHP", name="Philippine Peso"),
            'eur': Currency.objects.create(mnemonic='EUR', name="Euro")
        }
        # Create a company
        self.company = Company.objects.create(name="Test Company", currency=self.currencies['usd'])

        # Create BrokerCompany instances and link brokers
        self.broker_company_nium = BrokerCompany.objects.create(
            broker=BrokerProviderOption.NIUM,
            company=self.company,
            enabled=False
        )
        self.broker_company_nium.brokers.add(self.broker_nium)

        self.broker_company_corpay = BrokerCompany.objects.create(
            broker=BrokerProviderOption.CORPAY,
            company=self.company,
            enabled=True
        )
        self.broker_company_corpay.brokers.add(self.broker_corpay)

        self.broker_company_monex = BrokerCompany.objects.create(
            broker=BrokerProviderOption.MONEX,
            company=self.company,
            enabled=False
        )
        self.broker_company_monex.brokers.add(self.broker_monex)

        # Create CorpaySettings for the company
        CorpaySettings.objects.create(
            company=self.company,
            client_code=settings.CORPAY_CLIENT_LEVEL_CODE,
            signature=settings.CORPAY_CLIENT_LEVEL_SIGNATURE,
            average_volume=1000,
            credit_facility=10000.0,
            max_horizon=365,
            fee_wallet_id="test_wallet_id",
            pangea_beneficiary_id="test_pangea_id",
            user_code=settings.CORPAY_CLIENT_LEVEL_USER_CODE
        )

        # Create NiumSettings for the company
        NiumSettings.objects.create(
            company=self.company,
            customer_hash_id=settings.NIUM_CUSTOMER_HASH_ID
        )

        # Create MonexCompanySettings for the company
        MonexCompanySettings.objects.create(
            company=self.company,
            entity_id=settings.MONEX_ENTITY_ID,
            customer_id=settings.MONEX_CUSTOMER_ID,
            company_name=settings.MONEX_COMPANY_NAME
        )

        # Create Pairs
        self.pairs = {
            'usdeur': FxPair.objects.create(
                base_currency=self.currencies['usd'],
                quote_currency=self.currencies['eur'],
            ),
            'brleur': FxPair.objects.create(
                base_currency=self.currencies['brl'],
                quote_currency=self.currencies['eur'],
            )
        }

        # Create CNY execution
        self.cny_execs = {
            'corpay_usdeur': CnyExecution.objects.create(
                company=self.company,
                fxpair=self.pairs['usdeur'],
                spot_broker=BrokerProviderOption.CORPAY,
                fwd_broker=BrokerProviderOption.CORPAY,
                spot_rfq_type=CnyExecution.RfqTypes.API,
            ),
            'monex_brleur': CnyExecution.objects.create(
                company=self.company,
                fxpair=self.pairs['brleur'],
                spot_broker=BrokerProviderOption.MONEX,
                fwd_broker=BrokerProviderOption.MONEX,
                spot_rfq_type=CnyExecution.RfqTypes.API,
            )
        }

        # Setup bene mappings
        BeneficiaryFieldConfigService.create_or_update_beneficiary_field_configs()
        BeneficiaryFieldMappingService.create_or_update_beneficiary_field_mappings()
        BeneficiaryValueMappingService.create_or_update_value_mappings()

        # Create a user and associate with the company
        self.user = get_user_model().objects.create_user(
            email='user@test.com',
            password='testpass',
            company=self.company
        )

        self.client.force_authenticate(user=self.user)

        # Sample beneficiary data for each country
        self.bene_data = {
            'BRL': {
                "bank_name": "Banco do Brasil",
                "client_legal_entity": "BR",
                "beneficiary_postal": 1310100,
                "preferred_method": Beneficiary.PaymentSettlementMethod.SWIFT.value,
                "bank_routing_code_value_1": "123456",
                "beneficiary_phone": "+55 11 98765-4321",
                "payment_methods": [Beneficiary.PaymentSettlementMethod.SWIFT.value],
                "bank_postal": "01310-200",
                "beneficiary_country": "BR",
                "beneficiary_name": "Joao Silva",
                "beneficiary_alias": "Silva",
                "bank_account_number": "BR1800360305000010009795493C1",
                "destination_currency": "BRL",
                "beneficiary_region": "SAO PAULO",
                "bank_account_type": Beneficiary.BankAccountType.CHECKING.value,
                "identification_value": "123.456.789-00",
                "beneficiary_city": "São Paulo",
                "bank_account_number_type": Beneficiary.BankAccountNumberType.ACCOUNT_NUMBER.value,
                "identification_type": Beneficiary.IdentificationType.CPF.value,
                "settlement_methods": [Beneficiary.PaymentSettlementMethod.SWIFT.value],
                "bank_city": "São Paulo",
                "destination_country": "BR",
                "bank_country": "BR",
                "beneficiary_account_type": Beneficiary.AccountType.INDIVIDUAL.value,
                "classification": Beneficiary.Classification.INDIVIDUAL.value,
                "bank_address_1": "Rua da Consolação, 500",
                "beneficiary_address_1": "Avenida Paulista, 1000",
                "bank_routing_code_type_1": Beneficiary.BankRoutingCodeType.GENERIC.value,
                "bank_routing_code_type_2": Beneficiary.BankRoutingCodeType.SWIFT.value,
                "bank_routing_code_value_2": "BRLBBRSPXXX",
                "regulatory": {
                    "beneficiary_c_p_f": "01234567891",
                    "agency_code": "1234",
                    "contact_name": "Regulatory One",
                    "beneficiary_account_type": Beneficiary.RegulatoryBeneficiaryAccountType.SVGS.value.upper(),
                    "inter_bank_routing_code_1_value": "123456",
                    "inter_bank_routing_code_1_type": Beneficiary.BankRoutingCodeType.GENERIC.value,
                },
                "default_purpose": 4,
                "default_purpose_description": "Purchase of Good(s)"
            },
            'NPR': {
                "beneficiary_account_type": Beneficiary.AccountType.INDIVIDUAL.value,
                "destination_country": "NP",
                "destination_currency": "NPR",
                "payment_methods": [Beneficiary.PaymentSettlementMethod.SWIFT.value],
                "settlement_methods": [Beneficiary.PaymentSettlementMethod.SWIFT.value],
                "preferred_method": Beneficiary.PaymentSettlementMethod.SWIFT.value,
                "payment_reference": "NP-REF-001",
                "beneficiary_name": "Aarav Sharma",
                "beneficiary_alias": "Aarav",
                "beneficiary_address_1": "Thamel Marg, 123",
                "beneficiary_address_2": "Apartment 4B",
                "beneficiary_country": "NP",
                "beneficiary_region": "BAITADI",
                "beneficiary_postal": 44600,
                "beneficiary_city": "Kathmandu",
                "beneficiary_phone": "+977 98-1234-5678",
                "beneficiary_email": "aarav.sharma@email.com",
                "classification": Beneficiary.Classification.INDIVIDUAL.value,
                "identification_type": Beneficiary.IdentificationType.NATIONAL_ID.value,
                "identification_value": "1234567890",
                "bank_account_type": Beneficiary.BankAccountType.SAVING.value,
                "bank_code": "NBLN",
                "bank_account_number": "NP12G0200802486000005521481",
                "bank_account_number_type": Beneficiary.BankAccountNumberType.IBAN.value,
                "bank_name": "Nepal Bank Limited",
                "bank_country": "NP",
                "bank_region": "BAITADI",
                "bank_city": "Kathmandu",
                "bank_postal": "44601",
                "bank_address_1": "Dharma Path, 456",
                "bank_address_2": "New Road",
                "bank_branch_name": "Thamel Branch",
                "bank_routing_code_value_1": "NPBBNPKA",
                "bank_routing_code_type_1": Beneficiary.BankRoutingCodeType.SWIFT.value,
                "client_legal_entity": "NP",
                "remitter_beneficiary_relationship": "Family",
                "additional_fields": {},
                "regulatory": {
                    "beneficiary_bank_branch_name": "Thamel Branch"
                },
                "default_purpose": 4,
                "default_purpose_description": "Purchase of Good(s)"
            },
            'COP': {
                "beneficiary_account_type": Beneficiary.AccountType.CORPORATE.value,
                "destination_country": "CO",
                "destination_currency": "COP",
                "payment_methods": [Beneficiary.PaymentSettlementMethod.SWIFT.value],
                "settlement_methods": [Beneficiary.PaymentSettlementMethod.SWIFT.value],
                "preferred_method": Beneficiary.PaymentSettlementMethod.SWIFT.value,
                "payment_reference": "CO-REF-001",
                "beneficiary_name": "Isabella Gómez S.A.S.",
                "beneficiary_alias": "Isabella Empresa",
                "beneficiary_address_1": "Carrera 7, #71-21",
                "beneficiary_address_2": "Oficina 505",
                "beneficiary_country": "CO",
                "beneficiary_region": "CUNDINAMARCA",
                "beneficiary_postal": "110231",
                "beneficiary_city": "Bogotá",
                "beneficiary_phone": "+57 300 123 4567",
                "beneficiary_email": "isabella.gomez@empresa.co",
                "classification": Beneficiary.Classification.INDIVIDUAL.value,
                "identification_type": Beneficiary.IdentificationType.OTHERS.value,
                "identification_value": "9001234567",
                "bank_account_type": Beneficiary.BankAccountType.CHECKING.value,
                "bank_code": "001",
                "bank_account_number": "123456789012345",
                "bank_account_number_type": Beneficiary.BankAccountNumberType.ACCOUNT_NUMBER.value,
                "bank_name": "Bancolombia",
                "bank_country": "CO",
                "bank_region": "CUNDINAMARCA",
                "bank_city": "Bogotá",
                "bank_postal": "110221",
                "bank_address_1": "Calle 100, #7-33",
                "bank_address_2": "Torre 1, Piso 14",
                "bank_branch_name": "Sucursal Chapinero",
                "bank_routing_code_value_1": "COLCCOBBXXX",
                "bank_routing_code_type_1": Beneficiary.BankRoutingCodeType.SWIFT.value,
                "client_legal_entity": "CO",
                "additional_fields": {},
                "regulatory": {
                    "company_n_i_t_i_d": "9001234567",
                    "contact_name": "Carlos Rodriguez",
                    "beneficiary_account_type": "SAVINGS",
                    "beneficiary_cedula_i_d": "123456789"
                }
            },
            'CLP': {
                "beneficiary_account_type": Beneficiary.AccountType.INDIVIDUAL.value,
                "destination_country": "CL",
                "destination_currency": "CLP",
                "payment_methods": [Beneficiary.PaymentSettlementMethod.SWIFT.value],
                "settlement_methods": [Beneficiary.PaymentSettlementMethod.SWIFT.value],
                "preferred_method": Beneficiary.PaymentSettlementMethod.SWIFT.value,
                "payment_reference": "CL-REF-001",
                "beneficiary_name": "Mateo Rodríguez",
                "beneficiary_alias": "Mateo",
                "beneficiary_address_1": "Avenida Providencia 1760",
                "beneficiary_address_2": "Depto 303",
                "beneficiary_country": "CL",
                "beneficiary_region": "SANTIAGO",
                "beneficiary_postal": "7500000",
                "beneficiary_city": "Santiago",
                "beneficiary_phone": "+56 9 8765 4321",
                "beneficiary_email": "mateo.rodriguez@email.cl",
                "classification": Beneficiary.Classification.INDIVIDUAL.value,
                "identification_type": Beneficiary.IdentificationType.NATIONAL_ID.value,
                "identification_value": "12345678-9",
                "bank_account_type": Beneficiary.BankAccountType.CHECKING.value,
                "bank_code": "001",
                "bank_account_number": "00001234567",
                "bank_account_number_type": Beneficiary.BankAccountNumberType.ACCOUNT_NUMBER.value,
                "bank_name": "Banco de Chile",
                "bank_country": "CL",
                "bank_region": "SANTIAGO",
                "bank_city": "Santiago",
                "bank_postal": "8320000",
                "bank_address_1": "Ahumada 251",
                "bank_address_2": "Piso 5",
                "bank_branch_name": "Sucursal Providencia",
                "bank_routing_code_value_1": "BCHICLRMXXX",
                "bank_routing_code_type_1": Beneficiary.BankRoutingCodeType.SWIFT.value,
                "client_legal_entity": "CL",
                "additional_fields": {},
                "regulatory": {
                    "beneficiary_r_u_t": "123456789",
                    "contact_name": "Ana Martínez",
                    "RUT": "12345678-9"
                }
            },
            'IDR': {
                "beneficiary_account_type": Beneficiary.AccountType.CORPORATE.value,
                "destination_country": "ID",
                "destination_currency": "IDR",
                "payment_methods": [Beneficiary.PaymentSettlementMethod.SWIFT.value],
                "settlement_methods": [Beneficiary.PaymentSettlementMethod.SWIFT.value],
                "preferred_method": Beneficiary.PaymentSettlementMethod.SWIFT.value,
                "payment_reference": "ID-REF-001",
                "beneficiary_name": "PT Siti Nurhayati",
                "beneficiary_alias": "Siti Company",
                "beneficiary_address_1": "Jalan Sudirman No. 123",
                "beneficiary_address_2": "Lantai 15, Suite 1502",
                "beneficiary_country": "ID",
                "beneficiary_region": "JAVA",
                "beneficiary_postal": "12190",
                "beneficiary_city": "Jakarta",
                "beneficiary_phone": "+62 812-3456-7890",
                "beneficiary_email": "siti.nurhayati@company.co.id",
                "classification": Beneficiary.Classification.BUSINESS.value,
                "identification_type": Beneficiary.IdentificationType.OTHERS.value,
                "identification_value": "1234567890123",
                "bank_account_type": Beneficiary.BankAccountType.CHECKING.value,
                "bank_code": "014",
                "bank_account_number": "1234567890",
                "bank_account_number_type": Beneficiary.BankAccountNumberType.ACCOUNT_NUMBER.value,
                "bank_name": "Bank Central Asia",
                "bank_country": "ID",
                "bank_region": "JAVA",
                "bank_city": "Jakarta",
                "bank_postal": "10310",
                "bank_address_1": "Jalan M.H. Thamrin No. 1",
                "bank_address_2": "Menara BCA, Grand Indonesia",
                "bank_branch_name": "Jakarta Pusat Branch",
                "bank_routing_code_value_1": "CENAIDJA",
                "bank_routing_code_type_1": Beneficiary.BankRoutingCodeType.SWIFT.value,
                "client_legal_entity": "ID",
                "additional_fields": {},
                "regulatory": {
                    "beneficiary_bank_branch_name": "Jakarta Pusat Branch"
                },
                "default_purpose": 4,
                "default_purpose_description": "Purchase of Good(s)"
            },
            'PHP': {
                "beneficiary_account_type": Beneficiary.AccountType.INDIVIDUAL.value,
                "destination_country": "PH",
                "destination_currency": "PHP",
                "payment_methods": [Beneficiary.PaymentSettlementMethod.SWIFT.value],
                "settlement_methods": [Beneficiary.PaymentSettlementMethod.SWIFT.value],
                "preferred_method": Beneficiary.PaymentSettlementMethod.SWIFT.value,
                "payment_reference": "PH-REF-001",
                "beneficiary_name": "Juan Dela Cruz",
                "beneficiary_alias": "Juan",
                "beneficiary_address_1": "123 Rizal Avenue",
                "beneficiary_address_2": "Barangay 321",
                "beneficiary_country": "PH",
                "beneficiary_region": "LUZON",
                "beneficiary_postal": 1000,
                "beneficiary_city": "Manila",
                "beneficiary_phone": "+63 912 345 6789",
                "beneficiary_email": "juan.delacruz@email.ph",
                "classification": Beneficiary.Classification.INDIVIDUAL.value,
                "identification_type": Beneficiary.IdentificationType.NATIONAL_ID.value,
                "identification_value": "1234-5678-9012",
                "bank_account_type": Beneficiary.BankAccountType.SAVING.value,
                "bank_code": "021",
                "bank_account_number": "010030121345",
                "bank_account_number_type": Beneficiary.BankAccountNumberType.IBAN.value,
                "bank_name": "Bank of the Philippine Islands",
                "bank_country": "PH",
                "bank_region": "LUZON",
                "bank_city": "Makati",
                "bank_postal": "1226",
                "bank_address_1": "6768 Ayala Avenue",
                "bank_address_2": "BPI Building",
                "bank_branch_name": "Makati Main Branch",
                "bank_routing_code_value_1": "BOPIPHMM",
                "bank_routing_code_type_1": Beneficiary.BankRoutingCodeType.SWIFT.value,
                "client_legal_entity": "PH",
                "additional_fields": {},
                "regulatory": {}
            },
            'EUR': {
                "additional_fields": {},
                "regulatory": {},
                "beneficiary_account_type": "individual",
                "destination_country": "IT",
                "destination_currency": "EUR",
                "payment_methods": ["swift"],
                "settlement_methods": ["swift"],
                "preferred_method": "swift",
                "beneficiary_name": "Sun Productions LLc",
                "beneficiary_alias": "sunprod",
                "beneficiary_address_1": "address 1",
                "beneficiary_address_2": "address 2",
                "beneficiary_country": "IT",
                "beneficiary_region": "LAZIO",
                "beneficiary_postal": 837612,
                "beneficiary_city": "Rome",
                "beneficiary_phone": "+39 06 45774500",
                "beneficiary_email": "a@a.com",
                "classification": "individual",
                "date_of_birth": "1998-08-12",
                "identification_type": "passport",
                "identification_value": "1231231212412",
                "bank_account_type": "checking",
                "bank_account_number": "IT12G0200802486000005521487",
                "bank_account_number_type": "iban",
                "bank_name": "UNICREDIT SPA (BOLOGNA PARMEGGIANI)",
                "bank_country": "IT",
                "bank_city": "BOLOGNA",
                "bank_address_1": "VIA A. PARMEGGIANI 6",
                "bank_postal": "40131",
                "client_legal_entity": "US",
                "default_purpose": 4,
                "default_purpose_description": "Purchase of Good(s)",
                "bank_routing_code_value_1": "MRERITM1",
                "bank_routing_code_type_1": Beneficiary.BankRoutingCodeType.SWIFT.value
            },
            'EUR2': {
                "additional_fields": {},
                "regulatory": {},
                "beneficiary_account_type": "individual",
                "destination_country": "GB",
                "destination_currency": "EUR",
                "payment_methods": ["swift"],
                "settlement_methods": ["swift"],
                "preferred_method": "swift",
                "beneficiary_name": "Sun Productions LLc",
                "beneficiary_alias": "sunprod",
                "beneficiary_address_1": "address 1",
                "beneficiary_address_2": "address 2",
                "beneficiary_country": "GB",
                "beneficiary_region": "AB",
                "beneficiary_postal": "837612",
                "beneficiary_city": "ABERDEEN",
                "beneficiary_phone": "+441172345678",
                "beneficiary_email": "a@a.com",
                "classification": "individual",
                "date_of_birth": "1998-08-12",
                "identification_type": "passport",
                "identification_value": "1231231212412",
                "bank_account_type": "checking",
                "bank_account_number": "GB13BUKB60161331926" + str(randint(100, 999)),
                "bank_account_number_type": "iban",
                "bank_name": "BARCLAYS BANK UK PLC",
                "bank_country": "GB",
                "bank_city": "ABERDEEN",
                "bank_address_1": "1 CHURCHILL PLACE United Kingdom",
                "bank_postal": "01224",
                "client_legal_entity": "US",
                "bank_routing_code_value_1": "BUKBGB22123",
                "bank_routing_code_type_1": Beneficiary.BankRoutingCodeType.SWIFT.value
            }
        }

    def validate_beneficiary_data(self, data, schema):
        try:
            jsonschema.validate(instance=data, schema=schema)
            return True, None
        except jsonschema.exceptions.ValidationError as validation_error:
            # Log the detailed error path
            logger.error(f"Validation error path: {' -> '.join(str(path) for path in validation_error.path)}")
            logger.error(f"Validation error message: {validation_error.message}")
            return False, str(validation_error)

    def test_beneficiary_creation_flow(self):
        countries = [
            # ('BR', 'BRL'),  # Brazil
            # ('NP', 'NPR'),  # Nepal
            # ('CO', 'COP'),  # Colombia
            # ('CL', 'CLP'),  # Chile
            # ('ID', 'IDR'),  # Indonesia
            # ('PH', 'PHP'),  # Philippines
            ('IT', 'EUR'),  # Euro Bene, use this one to test Monex
            # ('GB', 'EUR2'),  # Euro Bene, use this one to test Nium
        ]

        for country_code, currency in countries:
            with self.subTest(country=country_code):
                beneficiary_data = self.bene_data[currency]
                currency = ''.join([i for i in currency if not i.isdigit()])
                # Step 1: Get validation schema
                validation_schema_url = reverse('v2:settlement:beneficiary-validation-schema')
                schema_data = {
                    "destination_country": country_code,
                    "bank_country": country_code,
                    "bank_currency": currency,
                    "beneficiary_account_type": beneficiary_data['beneficiary_account_type'],
                    "payment_method": beneficiary_data['preferred_method']
                }
                response = self.client.post(validation_schema_url, schema_data, format='json')
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                schema = response.data['merged']

                # Log the entire schema
                logger.debug(f"Validation schema for {currency}:")
                logger.debug(json.dumps(schema, indent=2))

                # Step 2: Validate sample data against schema

                # Log the beneficiary data
                logger.debug(f"Beneficiary data for {currency}:")
                logger.debug(json.dumps(beneficiary_data, indent=2))

                is_valid, error_message = self.validate_beneficiary_data(beneficiary_data, schema)
                self.assertTrue(is_valid, f"Sample data for {currency} failed validation: {error_message}")

                # Log the beneficiary data
                logger.debug(f"Beneficiary data for {currency}:")
                logger.debug(json.dumps(beneficiary_data, indent=2))

                # Step 3: Create beneficiary
                create_url = reverse('v2:settlement:beneficiary-list')
                response = self.client.post(create_url, beneficiary_data, format='json')
                logger.debug("test_beneficiary_creation_flow - Create Bene Response:")
                logger.debug(response.data)
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                beneficiary_id = response.data['beneficiary_id']

                # Step 4: Activate beneficiary
                activate_url = reverse('v2:settlement:beneficiary-activate')
                activate_data = {"identifier": beneficiary_id}
                response = self.client.post(activate_url, activate_data, format="json")
                self.assertEqual(response.status_code, status.HTTP_200_OK)

                # Verify beneficiary status
                beneficiary = Beneficiary.objects.get(beneficiary_id=beneficiary_id)
                self.assertEqual(beneficiary.status, Beneficiary.Status.SYNCED)

                # Step 5: Delete beneficiary
                delete_url = reverse('v2:settlement:beneficiary-detail', kwargs={'pk': beneficiary_id})
                response = self.client.delete(delete_url)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

                # Verify beneficiary is deleted
                with self.assertRaises(ObjectDoesNotExist):
                    Beneficiary.objects.get(beneficiary_id=beneficiary_id)
