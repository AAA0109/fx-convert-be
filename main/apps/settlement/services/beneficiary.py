import logging
import re
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from functools import lru_cache
from io import BytesIO
from typing import Dict, Optional, Union, Iterable, Iterator, Tuple, List

import requests
import yaml
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import JSONField
from django.utils.crypto import md5
from django_countries import countries
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.plumbing import force_instance, ComponentRegistry, build_serializer_context
from phonenumber_field.phonenumber import PhoneNumber
from requests.auth import HTTPDigestAuth
from rest_framework.test import APIRequestFactory

from main.apps.account.models import Company
from main.apps.broker.models import Broker, BrokerCompany, BrokerProviderOption
from main.apps.core.utils.dataclass import filter_dict_for_dataclass
from main.apps.core.utils.string import snake_to_title_case_with_acronyms
from main.apps.corpay.services.api.dataclasses.beneficiary import BeneficiaryRulesQueryParams, BeneficiaryRequestBody, \
    BeneficiaryListQueryParams
from main.apps.corpay.services.corpay import CorPayService
from main.apps.currency.models import Currency
from main.apps.monex.models import MonexBankType
from main.apps.monex.services.api.connectors.beneficiary import MonexBeneficiaryAPI
from main.apps.monex.services.api.dataclasses.beneficiary import BeneAddCurrency, BeneAddResponse, BeneGetBankPayload, \
    BeneGetBankResponse, BeneSaveInterBank, BeneSaveMainBank, BeneSavePayload
from main.apps.nium.services.api.dataclasses.beneficiary import (
    AddBenePayloadV2,
    UpdateBenePayloadV2,
    BeneficiaryValidationSchemaParams
)
from main.apps.nium.services.api.exceptions import BadRequest
from main.apps.nium.services.nium import NiumService
from main.apps.oems.models.cny import CnyExecution
from main.apps.settlement.api.serializers.beneficiary import BeneficiarySerializer
from main.apps.settlement.configurations.field.beneficiary import CORPAY_FIELD_CONFIG, NIUM_FIELD_CONFIG, \
    MONEX_FIELD_CONFIG
from main.apps.settlement.configurations.mappings.field.beneficiary import CORPAY_BENEFICIARY_FIELD_MAPPING, \
    NIUM_BENEFICIARY_FIELD_MAPPING, MONEX_BENEFICIARY_FIELD_MAPPING
from main.apps.settlement.configurations.mappings.value.beneficiary import CORPAY_BENEFICIARY_VALUE_MAPPING, MONEX_BANK_ACCOUNT_NUMBER_TYPE_VALUE_MAPPING, MONEX_BANK_ROUTING_CODE_TYPE_VALUE_MAPPING, \
    NIUM_BENEFICIARY_VALUE_MAPPING, MONEX_BENEFICIARY_VALUE_MAPPING
from main.apps.settlement.exceptions.beneficiary import InvalidPayoutMethod
from main.apps.settlement.models import Beneficiary, BeneficiaryFieldMapping, BeneficiaryFieldConfig, \
    BeneficiaryValueMapping, BeneficiaryBroker
from main.apps.settlement.models.beneficiary import BeneficiaryBrokerSyncResult

logger = logging.getLogger(__name__)


class BeneficiaryService(ABC):
    company: Company
    broker_company: BrokerCompany
    broker: Broker
    cache_timeout: int = 3600
    cache_enabled: bool = False

    def __init__(self, company: Company) -> None:
        self.company = company

    @abstractmethod
    def create_beneficiary(self, data: Dict) -> Beneficiary:
        pass

    @abstractmethod
    def update_beneficiary(self, beneficiary: Beneficiary) -> Beneficiary:
        pass

    @abstractmethod
    def delete_beneficiary(self, beneficiary: Beneficiary, reason: Optional[str] = None) -> None:
        pass

    @abstractmethod
    def sync_beneficiary_to_broker(self, beneficiary: Beneficiary) -> bool:
        pass

    @abstractmethod
    def sync_beneficiaries_from_broker(self) -> List[Beneficiary]:
        pass

    @abstractmethod
    def get_beneficiary_validation_schema(self, **kwargs) -> Dict:
        pass

    def map_beneficiary_field_value_to_broker(self, beneficiary: Union[Beneficiary, dict]) -> Union[
        Dict,
        BeneficiaryRequestBody
    ]:
        payload = {}

        # Get the field mappings for the specified broker
        field_mappings = BeneficiaryFieldMapping.objects.filter(brokers__in=[
                                                                self.broker])

        for mapping in field_mappings:
            beneficiary_field = mapping.beneficiary_field
            broker_field = mapping.broker_field

            # Get the value from the beneficiary model
            value = getattr(beneficiary, beneficiary_field, None)

            # If the value is not None, add it to the payload
            if value is None:
                continue
            if isinstance(value, Currency):
                value = value.mnemonic
            if isinstance(value, PhoneNumber):
                if beneficiary.beneficiary_country == 'ID':
                    value = value.raw_input.replace('+', '')
                else:
                    value = value.as_international
            if mapping.beneficiaryvaluemapping_set.count():
                value_mappings = list(
                    mapping.beneficiaryvaluemapping_set.all())
                if isinstance(value, list):
                    mapped_values = []
                    for val in value:
                        mapped_value = next(
                            (value_mapping.broker_value for value_mapping in value_mappings
                             if value_mapping.internal_value == val), None)
                        if mapped_value:
                            mapped_values.append(mapped_value)
                    value = mapped_values
                elif isinstance(value, dict):
                    list_key_value = []
                    for k in value.keys():
                        list_key_value.append({
                            'key': self.snake_to_camel(k),
                            'value': value.get(k, None)
                        })
                    value = list_key_value
                else:
                    value = next((value_mapping.broker_value for value_mapping in value_mappings
                                  if value_mapping.internal_value == value), None)
            payload[broker_field] = value

        # Include additional fields from the beneficiary model
        additional_fields = beneficiary.additional_fields or {}
        payload.update(additional_fields)

        return payload

    def convert_broker_data_to_beneficiary(self, data: Dict):
        bene_data = {}
        field_mapping = self.get_broker_field_mapping()
        value_mapping = self.get_broker_value_mapping()
        for broker_field, beneficiary_field in field_mapping.items():
            if broker_field in data:
                broker_value = data[broker_field]
                if broker_field in value_mapping:
                    mapping = value_mapping[broker_field]
                    if broker_value in mapping:
                        beneficiary_value = mapping[broker_value]
                    else:
                        beneficiary_value = broker_value
                else:
                    beneficiary_value = broker_value
                bene_data[beneficiary_field] = beneficiary_value

        return bene_data

    def get_broker_field_mapping(self, beneficiary_to_broker: bool = False):
        field_mapping = {}
        brokers = list(self.broker_company.brokers.all())
        mappings = BeneficiaryFieldMapping.objects.filter(brokers__in=brokers)
        for mapping in mappings:
            if beneficiary_to_broker:
                field_mapping[mapping.beneficiary_field] = mapping.broker_field
            else:
                field_mapping[mapping.broker_field] = mapping.beneficiary_field
        return field_mapping

    def get_broker_field_config(self):
        brokers = list(self.broker_company.brokers.all())
        configs = BeneficiaryFieldConfig.objects.filter(brokers__in=brokers)
        field_configs = {
            config.field_name: {
                'hidden': config.hidden,
                'validation_rule': config.validation_rule,
                'description': config.description,
                'is_required': config.is_required,
                'type': config.type
            }
            for config in configs
        }
        return field_configs

    def get_broker_value_mapping(self, beneficiary_to_broker: bool = False) -> dict:
        value_mapping = {}
        brokers = list(self.broker_company.brokers.all())
        mappings = BeneficiaryValueMapping.objects.filter(
            field_mapping__brokers__in=brokers)

        for mapping in mappings:
            if beneficiary_to_broker:
                beneficiary_field = mapping.field_mapping.beneficiary_field
                if beneficiary_field not in value_mapping:
                    value_mapping[beneficiary_field] = {}
                value_mapping[beneficiary_field][mapping.internal_value] = mapping.broker_value
            else:
                broker_field = mapping.field_mapping.broker_field
                if broker_field not in value_mapping:
                    value_mapping[broker_field] = {}
                value_mapping[broker_field][mapping.broker_value] = mapping.internal_value

        return value_mapping

    def update_bene_broker(self, beneficiary: Beneficiary, broker_beneficiary_id: Optional[str] = None,
                           is_delete: Optional[bool] = False) -> BeneficiaryBroker:
        bene_broker, created = BeneficiaryBroker.objects.get_or_create(beneficiary=beneficiary,
                                                                       broker=self.broker)
        if is_delete:
            bene_broker.deleted = True
            bene_broker.enabled = False
        elif broker_beneficiary_id:
            bene_broker.broker_beneficiary_id = str(broker_beneficiary_id)
        bene_broker.save()
        return bene_broker

    def track_beneficiary_broker_sync(self, beneficiary: Beneficiary, broker: Broker,
                                      error: Optional[str] = None) -> BeneficiaryBrokerSyncResult:
        sync_track, created = BeneficiaryBrokerSyncResult.objects.get_or_create(
            beneficiary=beneficiary,
            broker=broker
        )
        sync_track.last_sync = datetime.now(timezone.utc)
        sync_track.sync_errors = error
        sync_track.save()
        return sync_track

    def generate_unique_alias(self, company, original_alias):
        base_alias = original_alias  # Leave more room for the unique suffix
        unique_alias = base_alias
        suffix = 1
        while True:
            if not Beneficiary.objects.filter(company=company, beneficiary_alias=unique_alias).exists():
                return unique_alias
            unique_alias = f"{base_alias}-{suffix}"
            suffix += 1
            if suffix > 999:  # If we've tried 999 times, switch to using a UUID
                unique_alias = f"{base_alias}-{uuid.uuid4().hex[:8]}"
                if not Beneficiary.objects.filter(company=company, beneficiary_alias=unique_alias).exists():
                    return unique_alias

    @staticmethod
    def camel_to_snake(name):
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()

    @staticmethod
    def snake_to_camel(name):
        return ''.join(word.capitalize() for word in name.split('_'))

    @staticmethod
    def get_cache_key(key_string: str):

        # Encode the string to bytes
        key_bytes = key_string.encode('utf-8')

        # Generate the MD5 hash
        cache_key = md5(key_bytes).hexdigest()
        return cache_key

    @staticmethod
    def merge_validation_schemas(schemas):
        merged_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {},
            "required": []
        }

        def merge_properties(prop_list):
            merged_props = {}
            for prop in prop_list:
                for key, value in prop.items():
                    if key not in merged_props:
                        merged_props[key] = value
                    else:
                        merged_props[key] = merge_property_values(
                            key, merged_props[key], value)
            return merged_props

        def merge_property_values(key, value1, value2):
            if key == 'beneficiary_name':
                bene_name_title = 'Beneficiary Legal Name'
                if isinstance(value1, dict) and 'title' in value1:
                    value1['title'] = bene_name_title
                if isinstance(value2, dict) and 'title' in value2:
                    value2['title'] = bene_name_title
            elif key == 'beneficiary_region':
                bene_region_title = 'Beneficiary Region/State/Province'
                if isinstance(value1, dict) and 'title' in value1:
                    value1['title'] = bene_region_title
                if isinstance(value2, dict) and 'title' in value2:
                    value2['title'] = bene_region_title

            if isinstance(value1, dict) and isinstance(value2, dict):
                # Handle enum and const conflicts
                if ('enum' in value1 and 'const' in value2) or ('const' in value1 and 'enum' in value2):
                    enum_value = value1.get('enum') or value2.get('enum')
                    const_value = value1.get('const') or value2.get('const')

                    if isinstance(enum_value, list) and const_value is not None:
                        merged_enum = list(set(enum_value + [const_value]))
                        merged_dict = merge_dicts(value1, value2)
                        merged_dict['enum'] = merged_enum
                        if 'const' in merged_dict:
                            del merged_dict['const']
                        return merged_dict
                elif ('enum' in value1 and 'items' in value2) or ('items' in value1 and 'enum' in value2):
                    enum_value = value1.get('enum', value2.get('enum', []))
                    items_value = value1.get('items', value2.get('items', {}))
                    merged_value = {
                        'type': 'array',
                        'items': merge_dicts(items_value, {'enum': enum_value})
                    }
                    # Merge other properties
                    for k, v in {**value1, **value2}.items():
                        if k not in ['enum', 'items']:
                            merged_value[k] = v
                    return merged_value
                return merge_dicts(value1, value2)
            elif isinstance(value1, list) and isinstance(value2, list):
                return list(set(value1 + value2))
            else:
                # If one value is 'const' and the other is not, prefer 'const'
                if key == 'const':
                    return value1 if 'const' in value1 else value2
                return value2

        def merge_dicts(dict1, dict2):
            merged_dict = dict1.copy()
            for key, value in dict2.items():
                if key not in merged_dict:
                    merged_dict[key] = value
                else:
                    merged_dict[key] = merge_property_values(
                        key, merged_dict[key], value)
            return merged_dict

        def merge_conditionals(schema, merged, key):
            conditionals = schema.get(key, [])
            if conditionals:
                if key not in merged:
                    merged[key] = []
                merged[key].extend(conditionals)

        def make_hashable(obj):
            if isinstance(obj, list):
                return tuple(make_hashable(item) for item in obj)
            elif isinstance(obj, dict):
                return tuple(sorted((k, make_hashable(v)) for k, v in obj.items()))
            else:
                return obj

        def remove_duplicate_conditionals(merged, key):
            if key in merged:
                unique_conditionals = []
                seen_conditions = set()
                for conditional in merged[key]:
                    hashable_condition = make_hashable(conditional)
                    if hashable_condition not in seen_conditions:
                        unique_conditionals.append(conditional)
                        seen_conditions.add(hashable_condition)
                merged[key] = unique_conditionals

        # special handling for extra required fields
        def update_required(properties, required):
            if 'bank_routing_code_value_1' in required and 'bank_routing_code_value_1' in properties:
                required.append('bank_routing_code_type_1')
            if 'bank_routing_code_value_2' in required and 'bank_routing_code_value_2' in properties:
                required.append('bank_routing_code_type_2')

        def set_regulatory_to_required(merged_schema:Dict):
            """ set regulatory to required if there is a required regulatory rule """
            REG_KEY = 'regulatory'
            REG_RULES_KEY = 'regulatory_rules'
            if REG_KEY in merged_schema['properties'] and \
                REG_RULES_KEY in merged_schema['properties'] and \
                'properties' in merged_schema['properties'][REG_RULES_KEY]:

                rules:dict = merged_schema['properties'][REG_RULES_KEY]['properties']
                for k, v in rules.items():
                    if v.get('isRequired', False) and not REG_KEY in merged_schema['required']:
                        merged_schema['required'].append(REG_KEY)
                        merged_schema['properties'][REG_KEY]['nullable'] = False
                        break

        all_required = set()
        merged_if = {}
        merged_then = {}

        for schema in schemas:
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            merged_schema["properties"] = merge_properties(
                [merged_schema["properties"], properties])
            all_required.update(required)

            merge_conditionals(schema, merged_schema, "anyOf")
            merge_conditionals(schema, merged_schema, "oneOf")
            merge_conditionals(schema, merged_schema, "allOf")

            if_condition = schema.get("if", {})
            then_condition = schema.get("then", {})
            if if_condition:
                merged_if = merge_dicts(merged_if, if_condition)
            if then_condition:
                merged_then = merge_dicts(merged_then, then_condition)

        # update required

        merged_schema["required"] = list(all_required)

        remove_duplicate_conditionals(merged_schema, "anyOf")
        remove_duplicate_conditionals(merged_schema, "oneOf")
        remove_duplicate_conditionals(merged_schema, "allOf")

        if merged_if:
            merged_schema["if"] = merged_if
        if merged_then:
            merged_schema["then"] = merged_then

        update_required(merged_schema["properties"], merged_schema['required'])
        set_regulatory_to_required(merged_schema=merged_schema)

        return merged_schema


class CorpayBeneficiaryService(BeneficiaryService):
    api: CorPayService

    def __init__(self, company: Company) -> None:
        super().__init__(company)
        self.api = CorPayService()
        self.api.init_company(company)
        self.broker_company = BrokerCompany.objects.get(
            company=company, broker=BrokerProviderOption.CORPAY)
        self.broker = Broker.objects.get(
            broker_provider=BrokerProviderOption.CORPAY)

    def create_beneficiary(self, data: Dict) -> Dict:
        # Convert the beneficiary data to the broker payload
        payload = self.map_beneficiary_field_value_to_broker(data)

        # Call the CorPay API to create the beneficiary
        response = self.api.upsert_beneficiary(payload)

        # Extract the beneficiary data from the API response
        beneficiary_data = response.json()

        return beneficiary_data

    def update_beneficiary(self, beneficiary: Beneficiary) -> Dict:
        # Convert the updated beneficiary data to the broker payload
        payload = self.map_beneficiary_field_value_to_broker(
            beneficiary, self.broker_company.brokers.first())
        # Call the CorPay API to update the beneficiary
        response = self.api.upsert_beneficiary(
            beneficiary.beneficiary_id, payload)

        # Extract the updated beneficiary data from the API response
        updated_data = response.json()

        return updated_data

    def delete_beneficiary(self, beneficiary: Beneficiary, reason: Optional[str] = None) -> None:
        try:
            beneficiary_broker: BeneficiaryBroker = BeneficiaryBroker.objects.get(
                beneficiary=beneficiary,
                broker=self.broker
            )
            # Call the CorPay API to delete the beneficiary
            self.api.delete_beneficiary(
                beneficiary_broker.broker_beneficiary_id)

            # Update bene broker data
            bene_broker = self.update_bene_broker(
                beneficiary=beneficiary, is_delete=True)

            # Delete the CorpayBeneficiary object from the database
            # beneficiary.delete()
            self.track_beneficiary_broker_sync(
                beneficiary=beneficiary, broker=self.broker)
        except Exception as e:
            self.track_beneficiary_broker_sync(
                beneficiary=beneficiary, broker=self.broker, error=str(e))
            raise e

    def sync_beneficiary_to_broker(self, beneficiary: Beneficiary) -> bool:
        # Convert the beneficiary data to the broker payload
        payload = self.map_beneficiary_field_value_to_broker(beneficiary)

        try:
            # Call the CorPay API to sync the beneficiary to the broker
            response: dict = self.api.upsert_beneficiary(
                payload, beneficiary.company)
            bene_broker = self.update_bene_broker(beneficiary=beneficiary,
                                                  broker_beneficiary_id=response.get('client_integration_id', None))
            self.track_beneficiary_broker_sync(
                beneficiary=beneficiary, broker=self.broker)
            return True
        except Exception as e:
            self.track_beneficiary_broker_sync(
                beneficiary=beneficiary, broker=self.broker, error=str(e))
            raise e

    def sync_beneficiaries_from_broker(self) -> List[Beneficiary]:
        def _get_or_create_beneficiary(client_integration_id: str) -> Beneficiary:
            created = True
            try:
                beneficiary_broker = BeneficiaryBroker.objects.get(
                    broker_beneficiary_id=client_integration_id,
                    broker=self.broker,
                    beneficiary__company=self.company
                )
                created = False
                return beneficiary_broker.beneficiary, created
            except BeneficiaryBroker.DoesNotExist:
                try:
                    beneficiary = Beneficiary.objects.get(
                        external_id=client_integration_id)
                    created = False
                except Beneficiary.DoesNotExist:
                    beneficiary = Beneficiary(
                        external_id=client_integration_id,
                        company=self.company,
                        status=Beneficiary.Status.SYNCED
                    )
                    beneficiary.save()  # Save the beneficiary before creating BeneficiaryBroker

                    BeneficiaryBroker.objects.create(
                        broker_beneficiary_id=client_integration_id,
                        broker=self.broker,
                        beneficiary=beneficiary
                    )
                return beneficiary, created

        def _update_beneficiary_fields(beneficiary: Beneficiary, bene_data: dict, created: bool):
            # Update fields
            beneficiary.destination_country = bene_data.get(
                'destinationCountry')
            beneficiary.destination_currency = Currency.get_currency(
                bene_data.get('bankCurrency'))
            beneficiary.payment_methods = [method_map[m['method']] for m in bene_data.get('methods', []) if
                                           m['method'] in method_map]

            # Handle settlement_methods with fallback to preferred_method
            settlement_methods = [method_map[m] for m in bene_data.get('settlementMethods', '').split(',') if
                                  m in method_map]
            preferred_method = method_map.get(bene_data.get('preferredMethod'))
            if not settlement_methods and preferred_method:
                settlement_methods = [preferred_method]
            beneficiary.settlement_methods = settlement_methods

            beneficiary.preferred_method = preferred_method
            beneficiary.payment_reference = bene_data.get('paymentReference')
            beneficiary.beneficiary_account_type = Beneficiary.AccountType.INDIVIDUAL if bene_data.get(
                'beneClassification') == 'Individual' else Beneficiary.AccountType.CORPORATE
            beneficiary.beneficiary_name = bene_data.get('beneContactName')

            if created:
                # Generate a unique alias
                original_alias = f"{bene_data.get('beneContactName')}"
                beneficiary.beneficiary_alias = self.generate_unique_alias(
                    beneficiary.company, original_alias)

            beneficiary.preferred_method = method_map.get(
                bene_data.get('preferredMethod'))
            beneficiary.payment_reference = bene_data.get('paymentReference')
            beneficiary.beneficiary_account_type = Beneficiary.AccountType.INDIVIDUAL if bene_data.get(
                'beneClassification') == 'Individual' else Beneficiary.AccountType.CORPORATE
            beneficiary.beneficiary_name = bene_data.get('beneContactName')
            beneficiary.beneficiary_address_1 = bene_data.get('beneAddress1')
            beneficiary.beneficiary_address_2 = bene_data.get('beneAddress2')
            beneficiary.beneficiary_country = bene_data.get('beneCountry')
            beneficiary.beneficiary_region = bene_data.get('beneRegion')
            beneficiary.beneficiary_postal = bene_data.get('benePostal')
            beneficiary.beneficiary_city = bene_data.get('beneCity')
            beneficiary.beneficiary_phone = bene_data.get(
                'beneficiaryPhoneNumber')
            beneficiary.beneficiary_email = bene_data.get('beneEmail')
            beneficiary.classification = bene_data.get(
                'beneClassification', '').lower()
            beneficiary.bank_account_number = bene_data.get('accountNumber')
            beneficiary.bank_account_number_type = Beneficiary.BankAccountNumberType.IBAN if bene_data.get(
                'iban') else Beneficiary.BankAccountNumberType.ACCOUNT_NUMBER
            beneficiary.bank_name = bene_data.get('bankName')
            beneficiary.bank_country = bene_data.get('bankCountry')
            beneficiary.bank_region = bene_data.get("bankRegion")
            beneficiary.bank_city = bene_data.get('bankCity')
            beneficiary.bank_postal = bene_data.get('bankPostal')
            beneficiary.bank_address_1 = bene_data.get('bankAddressLine1')
            beneficiary.bank_address_2 = bene_data.get('bankAddressLine2')
            beneficiary.bank_routing_code_value_1 = None
            beneficiary.bank_routing_code_type_1 = None
            beneficiary.bank_routing_code_value_1 = bene_data.get(
                'routingCode')
            if not bene_data.get('swiftBicCode'):
                beneficiary.bank_routing_code_type_1 = routing_code_map.get(
                    bene_data.get('preferredMethod'))
            beneficiary.bank_routing_code_value_2 = None
            beneficiary.bank_routing_code_type_2 = None
            if bene_data.get('routingCode2'):
                beneficiary.bank_routing_code_value_2 = bene_data.get(
                    'routingCode2')
            beneficiary.bank_routing_code_value_3 = None
            beneficiary.bank_routing_code_type_3 = None
            if bene_data.get('swiftBicCode'):
                beneficiary.bank_routing_code_value_3 = bene_data.get(
                    'swiftBicCode')
                beneficiary.bank_routing_code_type_3 = Beneficiary.BankRoutingCodeType.SWIFT
            beneficiary.client_legal_entity = self.company.country.code
            beneficiary.regulatory = {item['key']: item['value'] for item in bene_data.get('regulatory', []) if
                                      'key' in item and 'value' in item}
            beneficiary.status = Beneficiary.Status.SYNCED

            # Intermediary bank details
            beneficiary.inter_bank_name = bene_data.get('iBankName')
            beneficiary.inter_bank_country = bene_data.get('iBankCountryISO')
            beneficiary.inter_bank_city = bene_data.get('iBankCity')
            beneficiary.inter_bank_region = bene_data.get('iBankProvince')
            beneficiary.inter_bank_postal = bene_data.get('iBankPostalCode')
            beneficiary.inter_bank_address_1 = bene_data.get('iBankAddress1')
            beneficiary.inter_bank_address_2 = bene_data.get('iBankAddress2')
            beneficiary.inter_bank_routing_code_value_1 = bene_data.get(
                'iBankSWIFTBIC')
            beneficiary.inter_bank_routing_code_type_1 = Beneficiary.BankRoutingCodeType.SWIFT if bene_data.get(
                'iBankSWIFTBIC') else None

        method_map = {
            'W': Beneficiary.PaymentSettlementMethod.SWIFT,
            'E': Beneficiary.PaymentSettlementMethod.LOCAL
        }
        routing_code_map = {
            'W': Beneficiary.BankRoutingCodeType.SWIFT,
            'E': Beneficiary.BankRoutingCodeType.ACH_CODE
        }
        beneficiaries_synced = []

        params = BeneficiaryListQueryParams()
        list_response = self.api.list_beneficiary(data=params)

        for row in list_response['data']['rows']:
            client_integration_id = row.get('clientIntegrationId')

            try:
                get_response = self.api.get_beneficiary(
                    client_integration_id=client_integration_id)
            except Exception as e:
                logger.exception(
                    f"Error fetching beneficiary {client_integration_id}: {e}")
                continue

            if 'bene' not in get_response:
                logger.warning(
                    f"No beneficiary data for {client_integration_id}")
                continue

            bene_data = get_response['bene']

            with transaction.atomic():
                beneficiary, created = _get_or_create_beneficiary(client_integration_id)
                _update_beneficiary_fields(beneficiary, bene_data, created)
                beneficiary.save()

                beneficiaries_synced.append(beneficiary)

        return beneficiaries_synced

    def get_beneficiary_validation_schema(self, destination_country: str, bank_country: str, bank_currency: str,
                                          beneficiary_account_type: str, payment_method: str) -> Dict:
        # Original string
        cache_key = self.get_cache_key(
            f"{destination_country}|{bank_country}|{bank_currency}|{beneficiary_account_type}|{payment_method}"
            f"|corpay_validation")
        payment_methods_mapping = {
            Beneficiary.PaymentSettlementMethod.LOCAL.value: 'E',
            Beneficiary.PaymentSettlementMethod.SWIFT.value: 'W',
            Beneficiary.PaymentSettlementMethod.WALLET.value: 'E',
            Beneficiary.PaymentSettlementMethod.CARD.value: 'E',
            Beneficiary.PaymentSettlementMethod.PROXY.value: 'E'
        }
        classification_mapping = {
            Beneficiary.AccountType.CORPORATE.value: "Business",
            Beneficiary.AccountType.INDIVIDUAL.value: "Individual"
        }
        if not cache.get(cache_key) or not self.cache_enabled:
            # Call the CorPay API to retrieve the beneficiary field requirements
            data = BeneficiaryRulesQueryParams(
                destinationCountry=destination_country,
                bankCountry=bank_country,
                bankCurrency=bank_currency,
                classification=classification_mapping[beneficiary_account_type],
                paymentMethods=payment_methods_mapping[payment_method]
            )
            response = self.api.get_beneficiary_rules(data=data)
            schema = self.convert_to_rules_to_json_schema(
                response, bank_currency)
            cache.set(cache_key, schema, self.cache_timeout)
            if not cache.get(cache_key):
                return schema
        return cache.get(cache_key)

    def convert_to_rules_to_json_schema(self, corpay_response: Dict, bank_currency: str):
        COUNTRY_FIELDS = (
            'destinationCountry',
            'bankCountry'
        )
        CURRENCY_FIELDS = (
            'bankCurrency'
        )

        def process_rule(rule, json_schema, is_regulatory=False):
            field_mappings = self.get_broker_field_mapping()
            field_configs = self.get_broker_field_config()
            value_mappings = self.get_broker_value_mapping()
            field_id = rule["id"]
            original_id = rule['id']
            if field_id in field_configs:
                # hide field from field config
                if field_configs.get(field_id).get('hidden'):
                    return
                # replace validation regex with our own rule if there's only 1
                if len(rule['validationRules']) == 1:
                    rule['validationRules'][0]['regEx'] = field_configs[field_id]['validation_rule']
            if field_id in field_mappings:
                field_id = field_mappings[field_id]

            title = field_id.replace("_", " ").title()

            field_schema = {
                "$id": f"#/properties/{field_id}",
                "type": "string",
                "title": title,
                "errorMessage": rule.get("errorMessage", "Invalid value for " + title)
            }

            validation_rules = []

            if "validationRules" in rule:
                for validation_rule in rule["validationRules"]:
                    rule_schema = {}
                    if "regEx" in validation_rule:
                        rule_schema["pattern"] = validation_rule["regEx"]
                    if "errorMessage" in validation_rule:
                        rule_schema["errorMessage"] = validation_rule["errorMessage"]
                    validation_rules.append(rule_schema)
            elif "regEx" in rule and rule["regEx"]:
                validation_rules.append({"pattern": rule["regEx"]})

            if "detailedRule" in rule:
                detailed_rules = rule["detailedRule"]
                for detailed_rule in detailed_rules:
                    if "isRequired" in detailed_rule:
                        field_schema["isRequired"] = detailed_rule["isRequired"]
                    if "value" in detailed_rule:
                        value_rules = detailed_rule["value"]
                        for value_rule in value_rules:
                            rule_schema = {}
                            if "regEx" in value_rule:
                                rule_schema["pattern"] = value_rule["regEx"]
                            if "errorMessage" in value_rule:
                                rule_schema["errorMessage"] = value_rule["errorMessage"]
                            validation_rules.append(rule_schema)

            if len(validation_rules) == 1:
                field_schema.update(validation_rules[0])
            elif len(validation_rules) > 1:
                field_schema["anyOf"] = validation_rules

            if "warning" in rule:
                field_schema["warning"] = rule["warning"]

            if "fieldFormatter" in rule:
                field_schema["fieldFormatter"] = rule["fieldFormatter"]

            if "defaultValue" in rule:
                if original_id in value_mappings and rule["defaultValue"] != "":
                    field_schema["default"] = value_mappings[original_id][rule["defaultValue"]]
                else:
                    field_schema["default"] = rule["defaultValue"]

            if rule.get("isRequired", False):
                if not is_regulatory:
                    json_schema["required"].append(field_id)

            if "valueSet" in rule:
                enums = []
                for value in rule["valueSet"]:
                    if original_id in value_mappings and value["id"] in value_mappings[original_id]:
                        enums.append(value_mappings[original_id][value["id"]])
                    else:
                        enums.append(value["id"])
                field_schema["enum"] = enums
                # special handling for payment and settlement methods
                if field_id in ("settlement_methods", "payment_methods"):
                    valid_methods = set(
                        item[0] for item in Beneficiary.PaymentSettlementMethod.choices)
                    filtered_methods = [
                        item for item in enums if item in valid_methods]
                    field_schema["enum"] = filtered_methods
                    field_schema["type"] = "array"

            # TODO: Patching this for now so corpay valueSet doesn't conflict with our internal enum
            if "links" in rule and original_id not in COUNTRY_FIELDS and original_id not in CURRENCY_FIELDS:
                for link in rule["links"]:
                    if link["method"] == "GET":
                        cache_key = self.get_cache_key(
                            f"corpay_proxy_request|{link['uri']}|{link['method']}")
                        if cache.get(cache_key):
                            response = cache.get(cache_key)
                        else:
                            response = self.api.proxy_request(
                                link['uri'], link['method'])
                            cache.set(cache_key, response, self.cache_timeout)
                        if "valueSet" in response:
                            field_schema["enum"] = [value['id']
                                                    for value in response['valueSet']]

            if "dependsOn" in rule:
                dependencies = [field_mappings.get(
                    dep, dep) for dep in rule["dependsOn"]]
                json_schema["dependencies"] = json_schema.get(
                    "dependencies", {})
                json_schema["dependencies"][field_id] = dependencies

            if is_regulatory:
                field_id = self.camel_to_snake(field_id)
                json_schema["properties"]["regulatory_rules"]["properties"][field_id] = field_schema
            else:
                json_schema["properties"][field_id] = field_schema

        json_schema = {
            "$id": f"beneficiary.{bank_currency.lower()}.corpay.json",
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": f"{bank_currency.upper()} Corpay Beneficiary Validations",
            "properties": {},
            "required": []
        }

        template_guide = corpay_response["templateGuide"]
        rules = template_guide["rules"]
        regulatory_rules = template_guide.get("regulatoryRules", [])

        for rule in rules:
            process_rule(rule, json_schema)

        if regulatory_rules:
            json_schema["properties"]["regulatory_rules"] = {
                "type": "object",
                "properties": {}
            }
            for rule in regulatory_rules:
                process_rule(rule, json_schema, is_regulatory=True)

        return json_schema

    def map_beneficiary_field_value_to_broker(self, beneficiary: Union[Beneficiary, dict]) -> BeneficiaryRequestBody:
        payload = super().map_beneficiary_field_value_to_broker(beneficiary)
        filtered_payload = filter_dict_for_dataclass(
            BeneficiaryRequestBody, payload)

        # handle templateIdentifier
        filtered_payload['templateIdentifier'] = beneficiary.beneficiary_id.hex

        # handle classification
        if beneficiary.classification == Beneficiary.Classification.INDIVIDUAL:
            filtered_payload['classification'] = "Individual"
        else:
            filtered_payload['classification'] = "Business"

        # handle routing code
        if beneficiary.bank_routing_code_value_1 is not None:
            filtered_payload['routingCode'] = beneficiary.bank_routing_code_value_1

        if beneficiary.regulatory is not None and beneficiary.regulatory != '':
            filtered_payload['regulatory'] = self.convert_regulatory(
                beneficiary.regulatory)

        if "accountHolderName" in filtered_payload:
            pattern = r'[^a-zA-Z0-9 .,&-]'
            account_holder_name = filtered_payload['accountHolderName']
            filtered_payload['accountHolderName'] = re.sub(
                pattern, '', account_holder_name)

        request_body = BeneficiaryRequestBody(
            **filtered_payload
        )
        return request_body

    def convert_regulatory(self, json_field: JSONField) -> List[Dict[str, str]]:
        if isinstance(json_field, dict):
            # If it's already a dict, use it directly
            json_data = json_field
        else:
            # If it's a JSONField, get its value
            json_data = json_field.value_from_object(
                json_field.model) if json_field.model else {}

        return [{"key": key if '_' not in key else self.snake_to_camel(key),
                 "value": str(value)
                } for key, value in json_data.items()]


class NiumBeneficiaryService(BeneficiaryService):
    api: NiumService

    def __init__(self, company: Company) -> None:
        super().__init__(company)
        self.api = NiumService()
        self.api.init_company(company)
        self.broker_company = BrokerCompany.objects.get(
            company=company, broker=BrokerProviderOption.NIUM)
        self.broker = Broker.objects.get(
            broker_provider=BrokerProviderOption.NIUM)

    def create_beneficiary(self, beneficiary: Beneficiary) -> Beneficiary:
        data = self.map_beneficiary_field_value_to_broker(beneficiary)
        return self.api.add_beneficiary(AddBenePayloadV2(**data))

    def update_beneficiary(self, beneficiary: Beneficiary) -> Beneficiary:
        data = self.map_beneficiary_field_value_to_broker(beneficiary)
        beneficiary_broker: BeneficiaryBroker = beneficiary.beneficiarybroker_set.get(
            broker__broker_provider=BrokerProviderOption.NIUM,
            company=self.company
        )
        beneficiary_id = beneficiary_broker.beneficiary_id
        return self.api.update_beneficiary(beneficiary_id, UpdateBenePayloadV2(**data))

    def delete_beneficiary(self, beneficiary: Beneficiary, reason: Optional[str] = None) -> None:
        try:
            beneficiary_broker: BeneficiaryBroker = BeneficiaryBroker.objects.get(
                beneficiary=beneficiary,
                broker=self.broker
            )
            response = self.api.delete_beneficiary(
                beneficiary_id=beneficiary_broker.broker_beneficiary_id)
            bene_broker = self.update_bene_broker(
                beneficiary=beneficiary, is_delete=True)
            self.track_beneficiary_broker_sync(
                beneficiary=beneficiary, broker=self.broker)
            return response
        except Exception as e:
            self.track_beneficiary_broker_sync(
                beneficiary=beneficiary, broker=self.broker, error=str(e))
            raise e

    def sync_beneficiary_to_broker(self, beneficiary: Beneficiary) -> bool:
        try:
            if beneficiary.beneficiarybroker_set.filter(broker__broker_provider=BrokerProviderOption.NIUM).exists():
                response: dict = self.update_beneficiary(beneficiary)
            else:
                response: dict = self.create_beneficiary(beneficiary)

            bene_broker = self.update_bene_broker(beneficiary=beneficiary,
                                                  broker_beneficiary_id=response.get('beneficiaryHashId', None))
            self.track_beneficiary_broker_sync(
                beneficiary=beneficiary, broker=self.broker)
            return True
        except Exception as e:
            self.track_beneficiary_broker_sync(
                beneficiary=beneficiary, broker=self.broker, error=str(e))
            raise e

    def sync_beneficiaries_from_broker(self) -> List[Beneficiary]:
        return []

    def get_beneficiary_validation_schema(self, bank_currency: str, payment_method: str, **kwargs) -> Iterable[Dict]:

        def replace_fields(schema, field_mapping, configs, value_mapping):

            if isinstance(schema, dict):
                new_schema = {}
                for key, value in schema.items():
                    if key == 'properties':
                        new_properties = {}
                        additional_fields = {}
                        required_fields = []  # List to store required fields
                        for prop_key, prop_value in value.items():
                            if prop_key in configs:
                                if configs.get(prop_key).get('hidden', False):
                                    continue
                                if configs.get(prop_key) and 'pattern' in prop_value:
                                    prop_value['pattern'] = configs.get(
                                        prop_key).get('validation_rule')

                            # Convert maxLength to integer if present
                            if 'maxLength' in prop_value:
                                try:
                                    prop_value['maxLength'] = int(
                                        prop_value['maxLength'])
                                except ValueError:
                                    # If conversion fails, keep the original value
                                    pass
                            if prop_key in field_mapping:
                                new_key = field_mapping[prop_key]
                                new_properties[new_key] = prop_value
                                if '$id' in prop_value:
                                    field_value_mapping = None
                                    if prop_key in value_mapping:
                                        field_value_mapping = value_mapping[prop_key]
                                    prop_value['$id'] = prop_value['$id'].replace(
                                        prop_key, new_key)
                                    if ('const' in prop_value and
                                            field_value_mapping is not None and
                                            prop_value['const'] in field_value_mapping
                                            ):
                                        prop_value['const'] = field_value_mapping[prop_value['const']]
                                    if 'enum' in prop_value:
                                        new_enum = []
                                        for enum in prop_value['enum']:
                                            if field_value_mapping is not None and enum in field_value_mapping:
                                                new_enum.append(
                                                    field_value_mapping[enum])
                                            else:
                                                new_enum.append(enum)
                                        prop_value['enum'] = new_enum
                            else:
                                snake_case_key = self.camel_to_snake(prop_key)
                                additional_fields[snake_case_key] = prop_value
                                if '$id' in prop_value:
                                    prop_value['$id'] = prop_value['$id'].replace(
                                        prop_key, snake_case_key)
                        if additional_fields:
                            new_properties['additional_fields'] = {
                                'type': 'object',
                                'properties': additional_fields
                            }
                        new_schema['properties'] = new_properties

                    elif key == 'required':
                        new_schema[key] = [field_mapping.get(
                            field, self.camel_to_snake(field)) for field in value]
                    else:
                        new_schema[key] = replace_fields(
                            value, field_mapping, configs, value_mapping)
                return new_schema
            elif isinstance(schema, list):
                return [replace_fields(item, field_mapping, configs, value_mapping) for item in schema]
            else:
                return schema

        key_string = f"{bank_currency}"
        if payment_method is not None:
            key_string += f"|{payment_method}"
        key_string += "|nium_bene_validation"
        cache_key = self.get_cache_key(key_string)

        if not cache.get(cache_key) or not self.cache_enabled:
            params = None
            if payment_method is not None:
                params = BeneficiaryValidationSchemaParams(
                    payoutMethod=payment_method.upper()
                )
            try:
                schemas = self.api.get_beneficiary_validation_schema(
                    currency=bank_currency, data=params)
            except BadRequest as e:
                raise InvalidPayoutMethod(
                    "Invalid payment method, please try requesting the validation schema with another payment method."
                )
            field_mapping = self.get_broker_field_mapping()
            value_mapping = self.get_broker_value_mapping()
            field_configs = self.get_broker_field_config()
            schemas_to_return = []
            for schema in schemas:
                replaced_schema = replace_fields(
                    schema, field_mapping, field_configs, value_mapping)
                schemas_to_return.append(replaced_schema)
            cache.set(cache_key, schemas_to_return, self.cache_timeout)
            if not cache.get(cache_key):
                return schemas_to_return
        return cache.get(cache_key)

    def map_beneficiary_field_value_to_broker(self, beneficiary: Beneficiary | dict) -> Dict | BeneficiaryRequestBody:
        data = super().map_beneficiary_field_value_to_broker(beneficiary)
        data['beneficiaryContactNumber'] = data['beneficiaryContactNumber'] \
            .replace('+', '').replace(' ', '')
        return data


class StreamWrapper:
    def __init__(self, stream):
        self.stream = stream
        self.buffer = BytesIO()

    def read(self, size=-1):
        while size < 0 or self.buffer.tell() < size:
            try:
                chunk = next(self.stream)
                self.buffer.write(chunk)
            except StopIteration:
                break
        self.buffer.seek(0)
        data = self.buffer.read(size)
        remainder = self.buffer.read()
        self.buffer = BytesIO(remainder)
        return data


class MonexBeneficiaryService(BeneficiaryService):
    schema_url = "https://developers.monexusa.com/spec/dev.v0.yaml"
    api = MonexBeneficiaryAPI

    def __init__(self, company: Company) -> None:
        super().__init__(company)
        self.broker_company = BrokerCompany.objects.get(company=company,
                                                        broker=BrokerProviderOption.MONEX)
        self.broker = Broker.objects.get(
            broker_provider=BrokerProviderOption.MONEX)
        self.api = MonexBeneficiaryAPI()

    @staticmethod
    def _map_pangea_purpose_to_monex(purpose: int):
        purpose = int(purpose)
        # PROD
        if settings.APP_ENVIRONMENT=='production':
            match purpose:
                case Beneficiary.Purpose.INTERCOMPANY_PAYMENT:
                    return Beneficiary.MonexPurposeProd.PAYMENT_TO_FUND_OVERSEAS_OPERATIONS.value[0]
                case Beneficiary.Purpose.PURCHASE_SALE_OF_GOODS:
                    return Beneficiary.MonexPurposeProd.PAYMENT_FOR_GOODS_PURCHASED.value[0]
                case Beneficiary.Purpose.PURCHASE_SALE_OF_SERVICES:
                    return Beneficiary.MonexPurposeProd.PAYMENT_FOR_SERVICES_PURCHASED.value[0]
                case Beneficiary.Purpose.PERSONNEL_PAYMENT:
                    return Beneficiary.MonexPurposeProd.PAYMENT_FOR_INTERNATIONAL_PAYROLL.value[0]
                case Beneficiary.Purpose.FINANCIAL_TRANSACTION:
                    # TODO: Determine if moving funds abroad or back to the US
                    # Beneficiary.MonexPurposeProd.REPATRIATE_FUNDS_TO_US
                    return Beneficiary.MonexPurposeProd.REPATRIATE_FUNDS_ABROAD.value[0]
                case Beneficiary.Purpose.OTHER:
                    return Beneficiary.MonexPurposeProd.OTHER.value[0]
       # DEV
        else:
            match purpose:
                case Beneficiary.Purpose.INTERCOMPANY_PAYMENT:
                    return Beneficiary.MonexPurposeDev.FUND_OVERSEAS.value[0]
                case Beneficiary.Purpose.PURCHASE_SALE_OF_GOODS:
                    return Beneficiary.MonexPurposeDev.GOODS_PURCHASED.value[0]
                case Beneficiary.Purpose.PURCHASE_SALE_OF_SERVICES:
                    return Beneficiary.MonexPurposeDev.SERVICES_PURCHASED.value[0]
                case Beneficiary.Purpose.PERSONNEL_PAYMENT:
                    return Beneficiary.MonexPurposeDev.INTERNATIONAL_PAYROLL.value[0]
                case Beneficiary.Purpose.FINANCIAL_TRANSACTION:
                    return Beneficiary.MonexPurposeDev.OTHER.value[0]
                case Beneficiary.Purpose.OTHER:
                    return Beneficiary.MonexPurposeDev.OTHER.value[0]

    def _map_bank_routing_code_type(self, routing_code_type:str) -> str:
        return MONEX_BANK_ROUTING_CODE_TYPE_VALUE_MAPPING.get(routing_code_type,
                                                              routing_code_type)

    def _map_bank_account_number_type(self, bank_acc_number_type:str) -> str:
        return MONEX_BANK_ACCOUNT_NUMBER_TYPE_VALUE_MAPPING.get(bank_acc_number_type,
                                                                bank_acc_number_type)

    def _fill_purpose_description(self, beneficiary:Beneficiary) -> str:
        # change get_default_purpose_display method if the field name change
        # min 10 chars of purpose desc. So I added 'Purpose' phrase to 'Other'
        purpose_description = beneficiary.default_purpose_description
        if beneficiary.default_purpose and \
            (purpose_description is None or not purpose_description or purpose_description.isdigit()):
            default_purpose_display = beneficiary.get_default_purpose_display()
            return default_purpose_display \
                if beneficiary.default_purpose != Beneficiary.Purpose.OTHER \
                    else f'{default_purpose_display} Purpose'
        return purpose_description

    def _find_valid_routing_pair(self, beneficiary:Beneficiary,
                                 bank_type:Optional[str] = MonexBankType.MAIN) -> Tuple[str, str]:
        route_type = route_value = ''
        pre = f'{bank_type}_' if bank_type == MonexBankType.INTER else ''
        for i in range(1, 4):
            rc_type = getattr(beneficiary, f'{pre}bank_routing_code_type_{i}')
            rc_val = getattr(beneficiary, f'{pre}bank_routing_code_value_{i}')
            if rc_type and rc_val:
                return rc_type, rc_val
            elif rc_type or rc_val:
                route_type = rc_type
                route_value = rc_val
        return route_type, route_value

    def _populate_non_bank_payload(self, beneficiary: Beneficiary) -> dict:
        field_mappings = BeneficiaryFieldMapping.objects.filter(brokers__in=[
                                                                self.broker])

        payload = {}
        for field_map in field_mappings:
            if '.' not in field_map.broker_field:
                value = getattr(beneficiary, field_map.beneficiary_field)
                if isinstance(value, Currency):
                    payload[field_map.broker_field] = value.mnemonic
                    continue
                payload[field_map.broker_field] = value

        payload['purposeId'] = self._map_pangea_purpose_to_monex(beneficiary.default_purpose).value
        purpose_description = self._fill_purpose_description(beneficiary=beneficiary)
        payload['purposeDescription'] = purpose_description
        return payload

    def _perform_monex_bene_flow(self, beneficiary: Beneficiary,
                                 broker_beneficiary_id: Optional[str] = None) -> dict:
        # Step 1. Prepare to add a bene
        response = self.api.beneficiary_add(company=self.company)
        bene_add_resp = BeneAddResponse(**response)
        bene_add_currency = self._can_add_beneficiary_currency(beneficiary.destination_currency,
                                                               bene_add_resp.common.currencies)
        if not bene_add_currency:
            raise ValidationError(
                "Unable to create Monex Beneficiary, currency not enabled.")
        country_id = self.api.country_code_to_monex_id(
            beneficiary.bank_country)

        # map bank account number type
        bank_account_number_type = self._map_bank_account_number_type(
            bank_acc_number_type=beneficiary.bank_account_number_type
        )

        bank_routing_code_type, bank_routing_code_value = \
            self._find_valid_routing_pair(beneficiary=beneficiary)
        # map bank routing code type
        bank_routing_code_type = self._map_bank_routing_code_type(
            routing_code_type=bank_routing_code_type
        )

        # Step 2. Validate bene's main bank info
        get_bank_payload = BeneGetBankPayload(
            accountNumber=beneficiary.bank_account_number,
            accountNumberType=bank_account_number_type,
            countryId=country_id,
            type=MonexBankType.MAIN.value,
            currencyCode=beneficiary.destination_currency.mnemonic,
            routingCodeType=bank_routing_code_type,
            routingCode=bank_routing_code_value
        )
        response = self.api.beneficiary_get_bank(company=self.company,
                                                 data=get_bank_payload)
        main_bank_resp = BeneGetBankResponse(**response)
        main_bank = BeneSaveMainBank(**main_bank_resp.dict())
        main_bank.accountNumber = beneficiary.bank_account_number

        # map inter bank account number type
        inter_bank_account_number_type = self._map_bank_account_number_type(
            bank_acc_number_type=beneficiary.inter_bank_account_number_type)

        inter_bank_routing_code_type, inter_bank_routing_code_value = \
            self._find_valid_routing_pair(beneficiary=beneficiary, bank_type=MonexBankType.INTER)
        # map inter bank routing code type
        inter_bank_routing_code_type = self._map_bank_routing_code_type(
            routing_code_type=inter_bank_routing_code_type
        )

        inter_bank = None
        if beneficiary.inter_bank_account_number:
            country_id = self.api.country_code_to_monex_id(
                beneficiary.inter_bank_country)
            get_bank_payload = BeneGetBankPayload(
                accountNumber=beneficiary.inter_bank_account_number,
                accountNumberType=inter_bank_account_number_type,
                countryId=country_id,
                type=MonexBankType.INTER.value,
                currencyCode=beneficiary.destination_currency.mnemonic,
                routingCodeType=inter_bank_routing_code_type,
                routingCode=inter_bank_routing_code_value
            )
            response = self.api.beneficiary_get_bank(company=self.company,
                                                     data=get_bank_payload)
            inter_bank_resp = BeneGetBankResponse(**response)
            inter_bank = BeneSaveInterBank(**inter_bank_resp.dict())
            inter_bank.accountNumber = beneficiary.inter_bank_account_number

        # Step 3. Adding a new bene
        non_bank_payload = self._populate_non_bank_payload(
            beneficiary=beneficiary)
        non_bank_payload['countryId'] = country_id
        non_bank_payload['currencyId'] = bene_add_currency.id

        # set id on monex beneficiary update
        if broker_beneficiary_id:
            non_bank_payload['id'] = int(broker_beneficiary_id)

        bene_save_payload = BeneSavePayload(mainBank=main_bank,
                                            interBank=inter_bank,
                                            **non_bank_payload)
        response = self.api.beneficiary_save(
            company=self.company, data=bene_save_payload)
        return response

    def _can_add_beneficiary_currency(self, bene_currency: Currency,
                                      currencies: Iterable[BeneAddCurrency]) -> Optional[BeneAddCurrency]:
        for bene_add_currency in currencies:
            if bene_currency.mnemonic == bene_add_currency.code:
                return bene_add_currency
        return None

    def create_beneficiary(self, beneficiary: Beneficiary) -> Dict:
        response = self._perform_monex_bene_flow(beneficiary=beneficiary)
        return response

    def update_beneficiary(self, beneficiary: Beneficiary) -> Dict:
        bene_broker = BeneficiaryBroker.objects.get(beneficiary=beneficiary,
                                                    broker=self.broker)
        response = self._perform_monex_bene_flow(beneficiary=beneficiary,
                                                 broker_beneficiary_id=bene_broker.broker_beneficiary_id)
        return response

    def delete_beneficiary(self, beneficiary: Beneficiary, reason: Optional[str] = None) -> None:
        try:
            beneficiary.status = Beneficiary.Status.DELETED
            beneficiary.save()
            bene_broker = self.update_bene_broker(
                beneficiary=beneficiary, is_delete=True)
            self.track_beneficiary_broker_sync(
                beneficiary=beneficiary, broker=self.broker)
        except Exception as e:
            self.track_beneficiary_broker_sync(
                beneficiary=beneficiary, broker=self.broker, error=str(e))
            raise e

    def sync_beneficiary_to_broker(self, beneficiary: Beneficiary) -> bool:
        try:
            if beneficiary.beneficiarybroker_set.filter(broker__broker_provider=BrokerProviderOption.MONEX).exists():
                response = self.update_beneficiary(beneficiary=beneficiary)
            else:
                response = self.create_beneficiary(beneficiary=beneficiary)
            bene_broker = self.update_bene_broker(beneficiary=beneficiary,
                                                  broker_beneficiary_id=response.get('id', None))
            self.track_beneficiary_broker_sync(
                beneficiary=beneficiary, broker=self.broker)
            return True
        except Exception as e:
            self.track_beneficiary_broker_sync(
                beneficiary=beneficiary, broker=self.broker, error=str(e))
            raise e

    def sync_beneficiaries_from_broker(self) -> List[Beneficiary]:
        def _get_or_create_beneficiary(bene_id):
            logger.info(f"Getting or creating beneficiary with ID: {bene_id}")
            try:
                beneficiary_broker = BeneficiaryBroker.objects.get(
                    broker_beneficiary_id=bene_id,
                    broker=self.broker,
                    beneficiary__company=self.company
                )
                return beneficiary_broker.beneficiary
            except BeneficiaryBroker.DoesNotExist:
                logger.info(
                    f"BeneficiaryBroker with ID {bene_id} does not exist")
                try:
                    beneficiary = Beneficiary.objects.get(external_id=bene_id)
                except Beneficiary.DoesNotExist:
                    logger.info(
                        f"Beneficiary with ID {bene_id} does not exist")
                    beneficiary = Beneficiary(
                        external_id=bene_id,
                        company=self.company,
                        status=Beneficiary.Status.SYNCED
                    )
                    logger.debug(f"Created beneficiary with ID {bene_id}")
                return beneficiary

        def _update_beneficiary_fields(beneficiary, bene_data):
            logger.info(
                f"Updating beneficiary fields for beneficiary ID: {beneficiary.id}")
            beneficiary_alias = self.generate_unique_alias(
                beneficiary.company, bene_data.get('nickname'))

            beneficiary.beneficiary_name = bene_data.get('name')
            beneficiary.beneficiary_alias = beneficiary_alias
            beneficiary.beneficiary_account_type = Beneficiary.AccountType.INDIVIDUAL if bene_data.get(
                'isIndividual') else Beneficiary.AccountType.CORPORATE
            beneficiary.beneficiary_country = self.api.monex_id_to_country_code(
                bene_data.get('countryId'))
            beneficiary.beneficiary_address_1 = bene_data.get('address1')
            beneficiary.beneficiary_address_2 = bene_data.get('address2')
            beneficiary.beneficiary_city = bene_data.get('city')
            beneficiary.beneficiary_region = bene_data.get('province')
            beneficiary.beneficiary_postal = bene_data.get('postal')
            beneficiary.beneficiary_email = bene_data.get('email')
            beneficiary.destination_currency = Currency.get_currency(
                self.api.monex_id_to_currency(bene_data.get('currencyId'))
            )
            # Update bank information
            main_bank = bene_data.get('mainBank', {})
            beneficiary.bank_name = main_bank.get('name')
            beneficiary.bank_country = self.api.monex_id_to_country_code(
                main_bank.get('countryId'))
            beneficiary.bank_city = main_bank.get('city')
            beneficiary.bank_address_1 = main_bank.get('address1')
            beneficiary.bank_address_2 = main_bank.get('address2')
            beneficiary.bank_postal = main_bank.get('postCode')
            beneficiary.bank_routing_code_type_1 = self.camel_to_snake(
                main_bank.get('routingCodeType')
            )
            beneficiary.bank_routing_code_value_1 = main_bank.get(
                'routingCode')
            beneficiary.bank_account_number = main_bank.get('accountNumber')
            beneficiary.bank_account_number_type = self.camel_to_snake(
                main_bank.get('accountNumberType')
            )
            beneficiary.status = Beneficiary.Status.SYNCED

            # Update intermediary bank information if available
            inter_bank = bene_data.get('interBank', {})
            if inter_bank:
                beneficiary.inter_bank_name = inter_bank.get('name')
                beneficiary.inter_bank_country = self.api.monex_id_to_country_code(
                    inter_bank.get('countryId'))
                beneficiary.inter_bank_city = inter_bank.get('city')
                beneficiary.inter_bank_address_1 = inter_bank.get('address1')
                beneficiary.inter_bank_address_2 = inter_bank.get('address2')
                beneficiary.inter_bank_postal = inter_bank.get('postCode')
                beneficiary.inter_bank_routing_code_type_1 = self.camel_to_snake(
                    inter_bank.get('routingCodeType')
                )
                beneficiary.inter_bank_routing_code_value_1 = inter_bank.get(
                    'routingCode')
            return beneficiary

        logger.info(
            f"Starting bene sync from Monex for company {self.company.pk} - {self.company.name}")
        beneficiaries_synced = []
        list_response = self.api.beneficiary_list(self.company)

        for row in list_response.get('rows', []):
            bene_id = row.get('id')
            if not bene_id:
                logger.warning(f"No beneficiary ID found in row: {row}")
                continue

            try:
                get_response = self.api.beneficiary_view(self.company, bene_id)
            except Exception as e:
                logger.exception(
                    f"Error fetching beneficiary for {bene_id}: {e}")
                continue

            if 'bene' not in get_response:
                logger.warning(f"No beneficiary data for {bene_id}")
                continue

            bene_data = get_response['bene']

            with transaction.atomic():
                try:
                    beneficiary = _get_or_create_beneficiary(bene_id)
                    beneficiary = _update_beneficiary_fields(
                        beneficiary, bene_data)
                    beneficiary.save()

                    bene_broker, created = BeneficiaryBroker.objects.update_or_create(
                        beneficiary=beneficiary,
                        broker=self.broker,
                        defaults={'broker_beneficiary_id': str(bene_id)}
                    )

                    self.track_beneficiary_broker_sync(
                        beneficiary=beneficiary, broker=self.broker)
                    beneficiaries_synced.append(beneficiary)
                except Exception as e:
                    logger.exception(
                        f"Error creating or updating beneficiary {bene_id}: {e}")

        return beneficiaries_synced

    def get_beneficiary_validation_schema(self, **kwargs) -> Optional[Dict]:
        cache_key = 'monex_beneficiary_schema'

        cached_schema = cache.get(cache_key)
        if cached_schema and self.cache_enabled:
            return cached_schema
        schema = {
            "$id": "beneficiary.monex.json",
            "$Schema": "http://json-schema.org/draft-07/schema#",
            "properties": {},
            "title": "Monex Beneficiary Validation",
            "type": "object",
        }
        original_schema = self._fetch_and_parse_schema()
        field_mapping = self.get_broker_field_mapping()
        value_mapping = self.get_broker_value_mapping()
        field_config = self.get_broker_field_config()
        properties, required = self._map_schema_properties(original_schema['properties'], original_schema['required'],
                                                           field_mapping, field_config,
                                                           value_mapping)
        schema['properties'] = properties
        schema['required'] = required

        if schema:
            cache.set(cache_key, schema, timeout=self.cache_timeout)
        else:
            logging.warning("Failed to extract schema from YAML")

        return schema

    def _fetch_and_parse_schema(self) -> Optional[Dict]:
        if not self._check_schema_api_credentials():
            return None

        try:
            response = self._fetch_yaml()
            schema = self._extract_schema(
                response.iter_lines(decode_unicode=True))
            return schema
        except requests.RequestException as e:
            logging.error(f"Error fetching the file: {e}")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")

        return None

    def _check_schema_api_credentials(self) -> bool:
        if settings.MONEX_DEV_USERNAME is None or settings.MONEX_DEV_PASSWORD is None:
            logging.warning(
                "MONEX_DEV_USERNAME or MONEX_DEV_PASSWORD is not set in Django settings")
            return False
        return True

    def _fetch_yaml(self) -> requests.Response:
        response = requests.get(
            self.schema_url,
            auth=HTTPDigestAuth(
                settings.MONEX_DEV_USERNAME,
                settings.MONEX_DEV_PASSWORD
            ),
            stream=True
        )
        response.raise_for_status()
        return response

    def _extract_schema(self, lines_iterator: Iterator[str]) -> Optional[Dict]:
        capture = False
        schema_content = []
        indent_level = None
        in_multiline = False
        multiline_indent = None

        for line in lines_iterator:
            stripped_line = line.strip()
            current_indent = len(line) - len(line.lstrip())

            if '/beneficiaries/save:' in line:
                capture = True
                indent_level = current_indent
                continue

            if capture:
                if 'schema:' in line:
                    indent_level = current_indent
                    schema_content = [line]
                    continue

                if in_multiline:
                    if current_indent > multiline_indent:
                        schema_content.append(line)
                        continue
                    else:
                        in_multiline = False

                if current_indent > indent_level or stripped_line.startswith('-'):
                    schema_content.append(line)
                    if stripped_line.endswith('>-') or stripped_line.endswith('|'):
                        in_multiline = True
                        multiline_indent = current_indent
                elif current_indent <= indent_level and schema_content:
                    if not stripped_line or stripped_line.startswith('#'):
                        continue  # Skip empty lines and comments
                    break  # End of schema section

        if not schema_content:
            logging.error("Failed to capture schema content")
            return None

        cleaned_yaml = self._clean_yaml('\n'.join(schema_content))
        return self._parse_yaml(cleaned_yaml)

    def _clean_yaml(self, yaml_str: str) -> str:
        lines = yaml_str.split('\n')
        cleaned_lines = []
        base_indent = None

        for line in lines:
            if line.strip():
                if base_indent is None:
                    base_indent = len(line) - len(line.lstrip())
                cleaned_line = line[base_indent:]
                cleaned_lines.append(cleaned_line)

        return '\n'.join(cleaned_lines)

    def _parse_yaml(self, yaml_str: str) -> Optional[Dict]:
        try:
            parsed_yaml = yaml.safe_load(yaml_str)
            # Navigate to the specific schema path
            schema = parsed_yaml.get('schema', {})

            if schema:
                return schema
            else:
                logging.warning(
                    "Specific schema path not found in the parsed YAML")
                return None  # Return the whole parsed YAML as a fallback
        except yaml.YAMLError as e:
            logging.error(f"Error parsing YAML content: {e}")
            return None

    def _map_schema_properties(self, broker_schema: Dict, broker_schema_required: List[str],
                               field_mapping: Dict, field_config: Dict, value_mapping: Dict) -> Tuple[Dict, List[str]]:
        mapped_schema = {}
        additional_fields = {}
        required_fields: List[str] = []

        def map_value(field_key: str, value: str) -> str:
            if field_key in value_mapping and value in value_mapping[field_key]:
                return value_mapping[field_key][value]
            return value

        def map_nested_fields(schema, prefix='', parent_required=False):
            local_required = schema.get('required', [])

            for key, value in schema.items():
                if key == 'required':
                    continue

                full_key = f"{prefix}{key}" if prefix else key
                mapped_key = field_mapping.get(full_key)

                # Check if the field is in field_config and not hidden
                config = field_config.get(full_key, {})
                if config.get('hidden', False):
                    continue

                # Check if the field is required
                field_is_required = (
                    parent_required and key in local_required) or full_key in broker_schema_required or config.get(
                    'is_required')

                if mapped_key:
                    mapped_schema[mapped_key] = {
                        'type': config.get('type') or value.get('type'),
                        'description': config.get('description') or value.get('description'),
                        'is_required': field_is_required
                    }
                    if 'enum' in value:
                        mapped_schema[mapped_key]['choices'] = [map_value(full_key, choice) for choice in
                                                                value['enum']]
                    if 'const' in value:
                        mapped_schema[mapped_key]['const'] = map_value(
                            full_key, value['const'])
                    if 'minLength' in value:
                        mapped_schema[mapped_key]['min_length'] = value['minLength']

                    if field_is_required:
                        required_fields.append(mapped_key)

                if isinstance(value, dict) and ('properties' in value or value.get('type') == 'object'):
                    new_prefix = f"{full_key}."
                    new_parent_required = parent_required or full_key in broker_schema_required
                    map_nested_fields(
                        value.get('properties', value), new_prefix, new_parent_required)
                elif not mapped_key:
                    nested_keys = full_key.split('.')
                    current_level = additional_fields
                    for nested_key in nested_keys[:-1]:
                        current_level = current_level.setdefault(
                            nested_key, {})
                    current_level[nested_keys[-1]] = {
                        'type': config.get('type') or value.get('type'),
                        'description': config.get('description') or value.get('description'),
                        'is_required': field_is_required
                    }
                    if 'enum' in value:
                        current_level[nested_keys[-1]]['choices'] = [map_value(full_key, choice) for choice in
                                                                     value['enum']]
                    if 'const' in value:
                        current_level[nested_keys[-1]
                                      ]['const'] = map_value(full_key, value['const'])
                    if 'minLength' in value:
                        current_level[nested_keys[-1]
                                      ]['min_length'] = value['minLength']

        try:
            map_nested_fields(broker_schema.get('properties', broker_schema))

            if additional_fields:
                mapped_schema['additional_fields'] = {
                    'type': 'object',
                    'properties': additional_fields
                }
        except Exception as e:
            print(f"Error in _map_schema_properties: {str(e)}")
            raise

        return mapped_schema, required_fields


class BeneficiaryServiceFactory(ABC):
    def __init__(self, company: Company):
        self.company = company

    def create_beneficiary_services(self, currency: Optional[Union[Currency, str]] = None) -> Iterable[
            BeneficiaryService]:
        beneficiary_services = []
        if currency:
            if isinstance(currency, str):
                currency = Currency.get_currency(currency=currency)

            configured_brokers = CompanyConfiguredBrokerProvider() \
                .get_configured_broker(company=self.company, currency=currency)

            for configured_broker in configured_brokers:
                if configured_broker == BrokerProviderOption.CORPAY:
                    if not self.company.corpaysettings:
                        continue
                    corpay_service = CorpayBeneficiaryService(self.company)
                    beneficiary_services.append(corpay_service)
                if configured_broker == BrokerProviderOption.NIUM:
                    if not self.company.niumsettings:
                        continue
                    nium_service = NiumBeneficiaryService(self.company)
                    beneficiary_services.append(nium_service)
                if configured_broker == BrokerProviderOption.MONEX:
                    if not self.company.monexcompanysettings:
                        continue
                    monex_service = MonexBeneficiaryService(self.company)
                    beneficiary_services.append(monex_service)
        else:
            broker_companies = BrokerCompany.objects.filter(
                company=self.company, enabled=True)
            for broker_company in broker_companies:
                if broker_company.broker == BrokerProviderOption.CORPAY:
                    if not self.company.corpaysettings:
                        continue
                    corpay_service = CorpayBeneficiaryService(self.company)
                    beneficiary_services.append(corpay_service)
                if broker_company.broker == BrokerProviderOption.NIUM:
                    if not self.company.niumsettings:
                        continue
                    nium_service = NiumBeneficiaryService(self.company)
                    beneficiary_services.append(nium_service)
                if broker_company.broker == BrokerProviderOption.MONEX:
                    if not self.company.monexcompanysettings:
                        continue
                    monex_service = MonexBeneficiaryService(self.company)
                    beneficiary_services.append(monex_service)
        return beneficiary_services


class CompanyConfiguredBrokerProvider:

    @staticmethod
    def get_configured_broker(company: Company, currency: Currency) -> List[str]:
        cny_exec = CnyExecution.objects \
            .filter(company=company, active=True, fxpair__quote_currency=currency) \
            .distinct('spot_broker', 'fwd_broker').values('spot_broker', 'fwd_broker')

        brokers = set()
        for item in list(cny_exec):
            brokers.update([item['spot_broker'], item['fwd_broker']])

        return list(brokers)


class BeneficiaryFieldConfigService:
    @staticmethod
    def create_or_update_beneficiary_field_configs():
        broker_configs = [
            (BrokerProviderOption.CORPAY, CORPAY_FIELD_CONFIG),
            (BrokerProviderOption.NIUM, NIUM_FIELD_CONFIG),
            (BrokerProviderOption.MONEX, MONEX_FIELD_CONFIG),
        ]

        for broker_provider, field_configs in broker_configs:
            try:
                broker = Broker.objects.get(broker_provider=broker_provider)
                for config in field_configs:
                    BeneficiaryFieldConfigService.get_or_create_field_config(
                        broker, config['field_name'], config
                    )
            except Broker.DoesNotExist:
                logger.error(
                    f"{broker_provider.label} broker does not exist, unable to populate field config")

    @staticmethod
    def get_or_create_field_config(broker, field_name, config):
        field_config = BeneficiaryFieldConfig.objects.filter(
            brokers__in=[broker], field_name=field_name
        ).first()

        if field_config:
            # Update the existing field configuration
            field_config.hidden = config['hidden']
            field_config.validation_rule = config['validation_rule']
            field_config.description = config['description']
            field_config.is_required = config['is_required']
            field_config.type = config['type']
            field_config.save()
            created = False
        else:
            # Create a new field configuration
            field_config = BeneficiaryFieldConfig.objects.create(
                field_name=field_name,
                hidden=config['hidden'],
                validation_rule=config['validation_rule'],
                description=config['description'],
                is_required=config['is_required'],
                type=config['type']
            )
            field_config.brokers.add(broker)
            created = True

        return field_config, created


class BeneficiaryFieldMappingService:
    @staticmethod
    def create_or_update_beneficiary_field_mappings():
        broker_mappings = [
            (BrokerProviderOption.CORPAY, CORPAY_BENEFICIARY_FIELD_MAPPING),
            (BrokerProviderOption.NIUM, NIUM_BENEFICIARY_FIELD_MAPPING),
            (BrokerProviderOption.MONEX, MONEX_BENEFICIARY_FIELD_MAPPING),
        ]

        for broker_provider, field_mappings in broker_mappings:
            try:
                broker = Broker.objects.get(broker_provider=broker_provider)
                for beneficiary_field, broker_field in field_mappings:
                    field_mapping, created = BeneficiaryFieldMapping.objects.get_or_create(
                        beneficiary_field=beneficiary_field,
                        broker_field=broker_field
                    )
                    field_mapping.brokers.add(broker)
            except Broker.DoesNotExist:
                pass


class BeneficiaryValueMappingService:
    @staticmethod
    def create_or_update_value_mappings():
        broker_mappings = [
            (BrokerProviderOption.CORPAY, CORPAY_BENEFICIARY_VALUE_MAPPING),
            (BrokerProviderOption.NIUM, NIUM_BENEFICIARY_VALUE_MAPPING),
            (BrokerProviderOption.MONEX, MONEX_BENEFICIARY_VALUE_MAPPING)
        ]

        for broker_provider, value_mappings in broker_mappings:
            try:
                broker = Broker.objects.get(broker_provider=broker_provider)
                field_mappings = BeneficiaryFieldMapping.objects.filter(brokers__in=[
                                                                        broker])

                for field_mapping in field_mappings:
                    if field_mapping.beneficiary_field in value_mappings:
                        broker_value_mappings = value_mappings[field_mapping.beneficiary_field]
                        for internal_value, broker_value in broker_value_mappings.items():
                            BeneficiaryValueMapping.objects.update_or_create(
                                field_mapping=field_mapping,
                                internal_value=internal_value,
                                defaults={'broker_value': broker_value}
                            )
            except Broker.DoesNotExist:
                logger.error(
                    f"{broker_provider.label} broker does not exist, unable to populate value mappings")


class BeneficiarySerializerService(ABC):
    cache = False
    cache_lifetime = 3600

    HIDDEN_FIELDS = (
        'beneficiary_id',
        'status',
        'brokers'
    )
    PAYMENT_METHOD_FIELDS = (
        'payment_methods',
        'preferred_method',
        'settlement_methods'
    )
    COUNTRY_FIELDS = {
        'beneficiary_country',
        'bank_country',
        'destination_country',
        'inter_bank_country',
        "client_legal_entity"
    }
    CURRENCY_FIELDS = {
        'destination_currency'
    }

    def __init__(self, viewset_class):
        self.serializer_class = BeneficiarySerializer
        self.viewset_class = viewset_class

    def get_schema(self, currency: str, payment_method: Optional[str] = None):
        cache_key = f"pangea_beneficiary_schema_{currency}_{payment_method}"
        if self.cache:
            cached_schema = cache.get(cache_key)
            if cached_schema:
                return cached_schema

        # Create a mock request
        factory = APIRequestFactory()
        mock_request = factory.post('/api/v2/schema')
        mock_request.user = AnonymousUser()  # Or use a real user if needed

        # Create an instance of the viewset
        viewset_instance = self.viewset_class()
        viewset_instance.request = mock_request
        viewset_instance.action = 'create'

        # Create an instance of the serializer with the mocked context
        serializer_context = build_serializer_context(viewset_instance)
        serializer_instance = force_instance(
            self.serializer_class(context=serializer_context))

        # Use AutoSchema to get the component schema
        auto_schema = AutoSchema()
        auto_schema.registry = ComponentRegistry()
        auto_schema.view = viewset_instance
        component_schema = auto_schema._map_serializer(
            serializer_instance, 'request')
        # Create a new dictionary for properties, excluding hidden fields
        new_properties = {}
        for property_name, property_value in component_schema['properties'].items():
            if "enum" in property_value:
                property_value['enum'] = [
                    value for value in property_value['enum'] if value]
            if property_name not in self.HIDDEN_FIELDS:
                if 'x-spec-enum-id' in property_value:
                    property_value.pop('x-spec-enum-id')
                if "items" in property_value:
                    items = property_value['items']
                    if 'x-spec-enum-id' in items:
                        items.pop('x-spec-enum-id')
                property_value['$id'] = '#/properties/' + property_name
                new_properties[property_name] = property_value
                if "additionalProperties" in property_value:
                    if isinstance(property_value['additionalProperties'], dict):
                        property_value['additionalProperties']['type'] = "string"
                    else:
                        property_value['additionalProperties'] = {
                            "type": "string"}
                if property_name in self.COUNTRY_FIELDS:
                    enum = self.get_countries_enum()
                    enum_names = self.get_countries_enum(labels=True)
                    property_value['enum'] = enum
                    property_value['enumNames'] = enum_names
                    property_value['choices'] = enum

                if property_name in self.CURRENCY_FIELDS:
                    enum = self.get_currencies_enum()
                    enum_names = self.get_currencies_enum(labels=True)
                    property_value['enum'] = enum
                    property_value['enumNames'] = enum_names
                    property_value['choices'] = enum

                if property_name == 'default_purpose':
                    enum = self.get_default_purposes_enum()
                    enum_names = self.get_default_purposes_enum(labels=True)
                    property_value['enum'] = enum
                    property_value['enumNames'] = enum_names
                    property_value['choices'] = enum

                if property_name == 'classification':
                    enum = self.get_classifications_enum()
                    enum_names = self.get_classifications_enum(labels=True)
                    property_value['enum'] = enum
                    property_value['enumNames'] = enum_names
                    property_value['choices'] = enum

                if property_name == 'identification_type':
                    enum = self.get_identification_types_enum()
                    enum_names = self.get_identification_types_enum(
                        labels=True)
                    property_value['enum'] = enum
                    property_value['enumNames'] = enum_names
                    property_value['choices'] = enum

            else:
                if property_name in component_schema['required']:
                    component_schema['required'].remove(property_name)

            if property_name == 'bank_account_type' and 'enum' in property_value and \
                Beneficiary.BankAccountType.CHECKING.value in property_value['enum']:
                property_value['default'] = Beneficiary.BankAccountType.CHECKING.value
            property_value['title'] = snake_to_title_case_with_acronyms(
                property_name)

        component_schema['properties'] = new_properties
        component_schema['$id'] = f"beneficiary.{currency.lower()}.pangea.json"
        component_schema['title'] = f"{currency} Pangea Beneficiary Validation"
        component_schema['$schema'] = f"http://json-schema.org/draft-07/schema#"

        if self.cache:
            cache.set(cache_key, component_schema, self.cache_lifetime)

        return component_schema

    @lru_cache(maxsize=None)
    def get_countries_enum(self, labels=False):
        ret = []
        for country in countries:
            if labels:
                ret.append(country.name)
            else:
                ret.append(country.code)
        return ret

    @lru_cache(maxsize=None)
    def get_currencies_enum(self, labels=False):
        ret = []
        for currency in Currency.objects.exclude(name__isnull=True):
            if labels:
                ret.append(currency.name)
            else:
                ret.append(currency.mnemonic)
        return ret

    @lru_cache(maxsize=None)
    def get_default_purposes_enum(self, labels=False):
        ret = []
        for key, value in Beneficiary.Purpose.choices:
            if labels:
                ret.append(value)
            else:
                ret.append(key)
        return ret

    @lru_cache(maxsize=None)
    def get_classifications_enum(self, labels=False):
        ret = []
        for key, value in Beneficiary.Classification.choices:
            if labels:
                ret.append(value)
            else:
                ret.append(key)
        return ret

    @lru_cache(maxsize=None)
    def get_identification_types_enum(self, labels=False):
        ret = []
        for key, value in Beneficiary.IdentificationType.choices:
            if labels:
                ret.append(value)
            else:
                ret.append(key)
