# Generated by Django 4.2.11 on 2024-05-30 00:14

from django.db import migrations


def populate_broker_companies(apps, schema_editor):
    Company = apps.get_model('account', 'Company')
    Broker = apps.get_model('broker', 'Broker')
    BrokerCompany = apps.get_model('broker', 'BrokerCompany')
    corpay_mp_broker = Broker.objects.get(broker_provider='CORPAY_MP')
    corpay_broker = Broker.objects.get(broker_provider='CORPAY')

    for company in Company.objects.all():
        broker_company, created = BrokerCompany.objects.get_or_create(
            broker="CORPAY",
            company=company
        )
        broker_company.brokers.add(corpay_mp_broker)
        broker_company.brokers.add(corpay_broker)


class Migration(migrations.Migration):
    dependencies = [
        ('broker', '0001_brokercompany'),
    ]

    operations = [
        migrations.RunPython(populate_broker_companies)
    ]
