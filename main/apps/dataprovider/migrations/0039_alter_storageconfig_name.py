# Generated by Django 4.2.11 on 2024-06-06 03:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "dataprovider",
            "0038_storageconfig_remove_collectorconfig_write_to_bq_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="storageconfig",
            name="name",
            field=models.CharField(max_length=255, null=True),
        ),
    ]
