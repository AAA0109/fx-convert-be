# Generated by Django 4.2.11 on 2024-07-03 00:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settlement', '0027_alter_wallet_account_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='wallet',
            name='method',
            field=models.CharField(blank=True, choices=[('rtp', 'RTP'), ('eft', 'EFT'), ('wire', 'Wire'), ('draft', 'Draft')], max_length=10, null=True),
        ),
    ]
