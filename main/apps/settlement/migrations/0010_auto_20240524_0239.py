# Generated by Django 4.2.11 on 2024-05-24 02:39

from django.db import migrations

from main.apps.settlement.services.beneficiary import BeneficiaryFieldMappingService


def populate_beneficiary_field_mappings(apps, schema_editor):
    BeneficiaryFieldMappingService.create_or_update_beneficiary_field_mappings()


class Migration(migrations.Migration):
    dependencies = [
        ('settlement', '0009_alter_beneficiaryfieldmapping_unique_together_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_beneficiary_field_mappings),
    ]