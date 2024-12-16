# Generated by Django 4.2.11 on 2024-06-11 17:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('broker', '0003_alter_brokercompany_company'),
        ('settlement', '0016_rename_bank_routing_code_1_type_beneficiary_bank_routing_code_type_1_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='beneficiary',
            name='remitter_beneficiary_relationship',
            field=models.TextField(blank=True, help_text='The relationship of the beneficiary with the remitter', null=True),
        ),
        migrations.CreateModel(
            name='BeneficiaryFieldConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_name', models.CharField(help_text='The field name', max_length=100)),
                ('hidden', models.BooleanField(default=False, help_text='Indicates whether the field should be hidden')),
                ('validation_rule', models.CharField(blank=True, help_text='Validation rule (regex) for the field', max_length=500, null=True)),
                ('description', models.TextField(blank=True, help_text='Description of the field', null=True)),
                ('is_required', models.BooleanField(default=False, help_text='Indicates whether the field is required')),
                ('brokers', models.ManyToManyField(help_text='The brokers associated with the field configuration', to='broker.broker')),
            ],
        ),
    ]
