# Generated by Django 4.2.15 on 2024-08-22 02:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settlement', '0038_alter_beneficiary_status_beneficiarybrokersyncresult'),
    ]

    operations = [
        migrations.AlterField(
            model_name='beneficiary',
            name='bank_routing_code_type_1',
            field=models.CharField(blank=True, choices=[('swift', 'SWIFT'), ('ifsc', 'IFSC'), ('sort_code', 'SORT Code'), ('ach_code', 'ACH Code'), ('branch_code', 'Branch Code'), ('bsb_code', 'BSB Code'), ('bank_code', 'Bank Code'), ('aba_code', 'ABA Code'), ('transit_code', 'Transit Code'), ('generic', 'Generic'), ('wallet', 'Wallet'), ('location_id', 'Location ID'), ('branch_name', 'Branch Name'), ('cnaps', 'CNAPS'), ('fedwire', 'Fedwire'), ('interac', 'Interac'), ('check', 'Check')], help_text='Bank Routing Code 1 Type', null=True),
        ),
        migrations.AlterField(
            model_name='beneficiary',
            name='bank_routing_code_type_2',
            field=models.CharField(blank=True, choices=[('swift', 'SWIFT'), ('ifsc', 'IFSC'), ('sort_code', 'SORT Code'), ('ach_code', 'ACH Code'), ('branch_code', 'Branch Code'), ('bsb_code', 'BSB Code'), ('bank_code', 'Bank Code'), ('aba_code', 'ABA Code'), ('transit_code', 'Transit Code'), ('generic', 'Generic'), ('wallet', 'Wallet'), ('location_id', 'Location ID'), ('branch_name', 'Branch Name'), ('cnaps', 'CNAPS'), ('fedwire', 'Fedwire'), ('interac', 'Interac'), ('check', 'Check')], help_text='Bank Routing Code 2 Type', null=True),
        ),
        migrations.AlterField(
            model_name='beneficiary',
            name='inter_bank_routing_code_type_1',
            field=models.CharField(blank=True, choices=[('swift', 'SWIFT'), ('ifsc', 'IFSC'), ('sort_code', 'SORT Code'), ('ach_code', 'ACH Code'), ('branch_code', 'Branch Code'), ('bsb_code', 'BSB Code'), ('bank_code', 'Bank Code'), ('aba_code', 'ABA Code'), ('transit_code', 'Transit Code'), ('generic', 'Generic'), ('wallet', 'Wallet'), ('location_id', 'Location ID'), ('branch_name', 'Branch Name'), ('cnaps', 'CNAPS'), ('fedwire', 'Fedwire'), ('interac', 'Interac'), ('check', 'Check')], help_text='Intermediary bank Routing Code 1 Type', null=True),
        ),
        migrations.AlterField(
            model_name='beneficiary',
            name='inter_bank_routing_code_type_2',
            field=models.CharField(blank=True, choices=[('swift', 'SWIFT'), ('ifsc', 'IFSC'), ('sort_code', 'SORT Code'), ('ach_code', 'ACH Code'), ('branch_code', 'Branch Code'), ('bsb_code', 'BSB Code'), ('bank_code', 'Bank Code'), ('aba_code', 'ABA Code'), ('transit_code', 'Transit Code'), ('generic', 'Generic'), ('wallet', 'Wallet'), ('location_id', 'Location ID'), ('branch_name', 'Branch Name'), ('cnaps', 'CNAPS'), ('fedwire', 'Fedwire'), ('interac', 'Interac'), ('check', 'Check')], help_text='Intermediary bank Routing Code 2 Type', null=True),
        ),
    ]
