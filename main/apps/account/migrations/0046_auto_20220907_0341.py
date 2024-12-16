# Generated by Django 3.2.8 on 2022-09-07 03:41

from django.db import migrations

def copy_user_stripe_data_to_company(apps, schema_editor):
    Company = apps.get_model('account', 'Company')
    companies = Company.objects.filter(account_owner__isnull=False)
    data = []
    for company in companies:
        company.stripe_customer_id = company.account_owner.stripe_customer_id
        company.stripe_setup_intent_id = company.account_owner.stripe_setup_intent_id
        data.append(company)
    Company.objects.bulk_update(data, ['stripe_customer_id', 'stripe_setup_intent_id'])

class Migration(migrations.Migration):

    dependencies = [
        ('account', '0045_auto_20220907_0253'),
    ]

    operations = [
        migrations.RunPython(copy_user_stripe_data_to_company)
    ]
