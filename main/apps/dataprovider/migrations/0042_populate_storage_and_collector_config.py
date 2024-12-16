# Generated by Django 4.2.11 on 2024-06-21 03:48

from django.db import migrations


def populate_storage_configs(apps, schema_editor):
    StorageConfig = apps.get_model('dataprovider', 'StorageConfig')
    StorageConfig.objects.get_or_create(
        name='BigQueryManager | GcpPubSub | RedisCache',
        defaults={
            'writer': 'main.apps.dataprovider.services.collectors.writer.BigQueryManager',
            'publisher': 'main.apps.dataprovider.services.collectors.publisher.GcpPubSub',
            'cache': 'main.apps.dataprovider.services.collectors.cache.RedisCache'
        }
    )
    StorageConfig.objects.get_or_create(
        name='GcpPubSub | RedisCache',
        defaults={
            'publisher': 'main.apps.dataprovider.services.collectors.publisher.GcpPubSub',
            'cache': 'main.apps.dataprovider.services.collectors.cache.RedisCache'
        }
    )


def populate_collector_config(apps, schema_editor):
    CollectorConfig = apps.get_model('dataprovider', 'CollectorConfig')
    StorageConfig = apps.get_model('dataprovider', 'StorageConfig')

    storage_config1 = StorageConfig.objects.get(
        name='BigQueryManager | GcpPubSub | RedisCache'
    )

    storage_config2 = StorageConfig.objects.get(
        name='GcpPubSub | RedisCache'
    )

    CollectorConfig.objects.get_or_create(
        name='corpay',
        defaults={
            'collector': 'main.apps.dataprovider.services.collectors.adapters.corpay_rfq_collector.CorpayRfqCollector',
            'storage_config': storage_config1,
            'kwargs': {"mkts": ["USDJPY"], "bases": ["USD"], "tenors": ["SPOT", "SN", "1W", "1M", "3M"]}
        }
    )

    CollectorConfig.objects.get_or_create(
        name='oer',
        defaults={
            'collector': 'main.apps.dataprovider.services.collectors.adapters.openex_collector.OpenExCollector',
            'storage_config': storage_config1,
            'kwargs': {"mkts": ["USDJPY"], "bases": ["USD", "EUR"], "tenors": ["SPOT", "SN", "1W", "1M", "3M"]}
        }
    )

    CollectorConfig.objects.get_or_create(
        name='verto',
        defaults={
            'collector': 'main.apps.dataprovider.services.collectors.adapters.verto_rfq_collector.VertoRfqCollector',
            'storage_config': storage_config2,
            'kwargs': {"mkts": ["USDJPY"]}
        }
    )


class Migration(migrations.Migration):
    dependencies = [
        ("dataprovider", "0041_backfill_option_ice_sftp"),
    ]

    operations = [
        migrations.RunPython(populate_storage_configs),
        migrations.RunPython(populate_collector_config),
    ]
