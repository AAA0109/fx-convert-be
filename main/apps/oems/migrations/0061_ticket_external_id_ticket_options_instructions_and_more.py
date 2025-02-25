# Generated by Django 4.2.11 on 2024-04-11 22:02

from django.db import migrations, models
import main.apps.oems.backend.utils


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0060_ticket_lock_side'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='external_id',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ticket',
            name='options_instructions',
            field=models.JSONField(blank=True, encoder=main.apps.oems.backend.utils.DateTimeEncoder, null=True),
        ),
        migrations.AddField(
            model_name='ticket',
            name='spot_rate',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ticket',
            name='style',
            field=models.CharField(blank=True, default='parent', help_text='Specifies the ticket style.', max_length=32, null=True, verbose_name=[('parent', 'parent'), ('child', 'child'), ('virtual_parent', 'virtual_parent'), ('virtual_child', 'virtual_child')]),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='instrument_type',
            field=models.CharField(blank=True, choices=[('spot', 'SPOT'), ('fwd', 'FWD'), ('ndf', 'NDF'), ('option_strategy', 'OPTION_STRATEGY')], null=True),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='time_in_force',
            field=models.CharField(choices=[('10sec', '10s'), ('1min', '1min'), ('1hr', '1hr'), ('gtc', 'GTC'), ('day', 'DAY'), ('indicative', 'INDICATIVE')], help_text='Specifies the duration for which the transaction is valid.', max_length=16),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='with_care',
            field=models.BooleanField(default=True, help_text='Specifies whether the transaction should be handled manually by the desk.'),
        ),
    ]
