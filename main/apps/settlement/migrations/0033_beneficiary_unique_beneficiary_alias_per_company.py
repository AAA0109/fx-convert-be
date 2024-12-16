# Generated by Django 4.2.14 on 2024-08-09 18:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("settlement", "0032_alter_beneficiary_beneficiary_alias"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="beneficiary",
            constraint=models.UniqueConstraint(
                fields=("company", "beneficiary_alias"),
                name="unique_beneficiary_alias_per_company",
            ),
        ),
    ]