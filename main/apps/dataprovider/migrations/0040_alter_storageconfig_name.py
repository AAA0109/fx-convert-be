# Generated by Django 4.2.11 on 2024-06-06 03:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dataprovider", "0039_alter_storageconfig_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="storageconfig",
            name="name",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
