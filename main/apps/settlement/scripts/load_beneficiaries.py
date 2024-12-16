import csv
import os
from datetime import datetime
from django.db import transaction
from django.conf import settings

from main.apps.account.models import Company
from main.apps.settlement.models import Beneficiary


def run():
    load_beneficiaries_from_csv()


def load_beneficiaries_from_csv():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file_path = os.path.join(current_dir, 'benes.csv')

    with open(csv_file_path, 'r') as file:
        csv_reader = csv.DictReader(file)
        pangea_id = settings.CORPAY_PANGEA_COMPANY_ID
        company = Company.objects.get(pk=pangea_id)

        with transaction.atomic():
            for row in csv_reader:
                beneficiary = Beneficiary(
                    id=row['id'],
                    created=datetime.strptime(
                        row['created'], '%Y-%m-%d %H:%M:%S'),
                    modified=datetime.strptime(
                        row['modified'], '%Y-%m-%d %H:%M:%S'),
                    destination_country=row['destination_country'],
                    destination_currency_id=row['destination_currency'],
                    payment_methods=row['payment_methods'],
                    settlement_methods=row['settlement_methods'],
                    preferred_method=row['preferred_method'],
                    payment_reference=row['payment_reference'],
                    beneficiary_account_type=row['beneficiary_account_type'],
                    beneficiary_name=row['beneficiary_name'],
                    beneficiary_alias=row['beneficiary_alias'],
                    beneficiary_address_1=row['beneficiary_address_1'],
                    beneficiary_address_2=row['beneficiary_address_2'],
                    beneficiary_country=row['beneficiary_country'],
                    beneficiary_region=row['beneficiary_region'],
                    beneficiary_postal=row['beneficiary_postal'],
                    beneficiary_city=row['beneficiary_city'],
                    beneficiary_phone=row['beneficiary_phone'],
                    beneficiary_email=row['beneficiary_email'],
                    classification=row['classification'],
                    date_of_birth=row['date_of_birth'] if row['date_of_birth'] else None,
                    identification_type=row['identification_type'],
                    identification_value=row['identification_value'],
                    bank_account_type=row['bank_account_type'],
                    bank_code=row['bank_code'],
                    bank_account_number=row['bank_account_number'],
                    bank_account_number_type=row['bank_account_number_type'],
                    bank_name=row['bank_name'],
                    bank_country=row['bank_country'],
                    bank_region=row['bank_region'],
                    bank_city=row['bank_city'],
                    bank_postal=row['bank_postal'],
                    bank_address_1=row['bank_address_1'],
                    bank_address_2=row['bank_address_2'],
                    bank_branch_name=row['bank_branch_name'],
                    bank_instruction=row['bank_instruction'],
                    bank_routing_code_value_1=row['bank_routing_code_value_1'],
                    bank_routing_code_type_1=row['bank_routing_code_type_1'],
                    bank_routing_code_value_2=row['bank_routing_code_value_2'],
                    bank_routing_code_type_2=row['bank_routing_code_type_2'],
                    bank_routing_code_value_3=row['bank_routing_code_value_3'],
                    bank_routing_code_type_3=row['bank_routing_code_type_3'],
                    inter_bank_account_type=row['inter_bank_account_type'],
                    inter_bank_code=row['inter_bank_code'],
                    inter_bank_account_number=row['inter_bank_account_number'],
                    inter_bank_account_number_type=row['inter_bank_account_number_type'],
                    inter_bank_name=row['inter_bank_name'],
                    inter_bank_country=row['inter_bank_country'],
                    inter_bank_region=row['inter_bank_region'],
                    inter_bank_city=row['inter_bank_city'],
                    inter_bank_postal=row['inter_bank_postal'],
                    inter_bank_address_1=row['inter_bank_address_1'],
                    inter_bank_address_2=row['inter_bank_address_2'],
                    inter_bank_branch_name=row['inter_bank_branch_name'],
                    inter_bank_instruction=row['inter_bank_instruction'],
                    inter_bank_routing_code_value_1=row['inter_bank_routing_code_value_1'],
                    inter_bank_routing_code_type_1=row['inter_bank_routing_code_type_1'],
                    inter_bank_routing_code_value_2=row['inter_bank_routing_code_value_2'],
                    inter_bank_routing_code_type_2=row['inter_bank_routing_code_type_2'],
                    inter_bank_routing_code_value_3=row['inter_bank_routing_code_value_3'],
                    inter_bank_routing_code_type_3=row['inter_bank_routing_code_type_3'],
                    client_legal_entity=row['client_legal_entity'],
                    proxy_type=row['proxy_type'],
                    proxy_value=row['proxy_value'],
                    remitter_beneficiary_relationship=row['remitter_beneficiary_relationship'],
                    further_name=row['further_name'],
                    further_account_number=row['further_account_number'],
                    beneficiary_id=row['beneficiary_id'],
                    external_id=row['external_id'],
                    company=company,
                    status=Beneficiary.Status.DRAFT,
                    reason=row['reason'],
                    additional_fields=row['additional_fields'],
                    regulatory=row['regulatory'],
                    default_purpose=row['default_purpose'],
                    default_purpose_description=row['default_purpose_description']
                )
                beneficiary.save()

    print("Beneficiaries loaded successfully.")
