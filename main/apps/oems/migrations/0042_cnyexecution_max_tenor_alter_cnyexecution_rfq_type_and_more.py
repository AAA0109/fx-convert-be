# Generated by Django 4.2.10 on 2024-03-08 15:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0041_manualrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='cnyexecution',
            name='max_tenor',
            field=models.CharField(choices=[('ON', 'ON'), ('TN', 'TN'), ('spot', 'Spot'), ('SN', 'SN'), ('SW', 'SW'), ('1W', '1W'), ('2W', '2W'), ('3W', '3W'), ('1M', '1M'), ('2M', '2M'), ('3M', '3M'), ('4M', '4M'), ('5M', '5M'), ('6M', '6M'), ('7M', '7M'), ('8M', '8M'), ('9M', '9M'), ('1Y', '1Y'), ('IMM1', 'IMM1'), ('IMM2', 'IMM2'), ('IMM3', 'IMM3'), ('IMM4', 'IMM4'), ('EOM1', 'EOM1'), ('EOM2', 'EOM2'), ('EOM3', 'EOM3'), ('EOM4', 'EOM4'), ('EOM5', 'EOM5'), ('EOM6', 'EOM6'), ('EOM7', 'EOM7'), ('EOM8', 'EOM8'), ('EOM9', 'EOM9'), ('EOM10', 'EOM10'), ('EOM11', 'EOM11'), ('EOM12', 'EOM12')], default='1Y', help_text='The maximum allowed tenor of the transaction.', max_length=10),
        ),
        migrations.AlterField(
            model_name='cnyexecution',
            name='rfq_type',
            field=models.CharField(choices=[('api', 'API'), ('manual', 'MANUAL'), ('unsupported', 'UNSUPPORTED'), ('indicative', 'INDICATIVE'), ('norfq', 'NORFQ')], default='unsupported', max_length=16),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='date_conversion',
            field=models.CharField(blank=True, choices=[('modified_follow', 'Modified Follow'), ('reject', 'Reject'), ('next', 'Next'), ('previous', 'Previous')], null=True),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='rfq_type',
            field=models.TextField(blank=True, choices=[('api', 'API'), ('manual', 'MANUAL'), ('unsupported', 'UNSUPPORTED'), ('indicative', 'INDICATIVE'), ('norfq', 'NORFQ')], null=True),
        ),
    ]