# Generated by Django 4.2.14 on 2024-08-13 23:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("settlement", "0033_beneficiary_unique_beneficiary_alias_per_company"),
    ]

    operations = [
        migrations.AddField(
            model_name="beneficiaryfieldconfig",
            name="type",
            field=models.CharField(
                blank=True, help_text="The field data type", max_length=32, null=True
            ),
        ),
    ]
