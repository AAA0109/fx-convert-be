# Generated by Django 4.2.10 on 2024-03-06 16:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0038_rename_order_size_limit_cnyexecution_max_order_size_from_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticket',
            name='rfq_type',
            field=models.TextField(blank=True, choices=[('api', 'API'), ('manual', 'MANUAL'), ('unsupported', 'UNSUPPORTED'), ('indicative', 'INDICATIVE')], null=True),
        ),
    ]