# Generated by Django 4.2.15 on 2024-09-06 21:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0104_merge_20240904_0028'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticket',
            name='phase',
            field=models.CharField(blank=True, choices=[('PRETRADE', 'Pretrade'), ('TRADE', 'Trade'), ('SETTLE', 'Settle'), ('RECON', 'Recon')], max_length=64, null=True),
        ),
    ]
