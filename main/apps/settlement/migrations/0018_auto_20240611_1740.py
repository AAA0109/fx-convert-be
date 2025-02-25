# Generated by Django 4.2.11 on 2024-06-11 17:40
import logging

from django.db import migrations

from main.apps.settlement.services.beneficiary import BeneficiaryFieldConfigService

logger = logging.getLogger(__name__)


def seed_beneficiary_field_config(apps, schema_editor):
    try:
        BeneficiaryFieldConfigService.create_or_update_beneficiary_field_configs()
    except Exception as e:
        logger.error("Unable to update bene field configs: " + e.__str__())


class Migration(migrations.Migration):
    dependencies = [
        ('settlement', '0017_beneficiary_remitter_beneficiary_relationship_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_beneficiary_field_config)
    ]
