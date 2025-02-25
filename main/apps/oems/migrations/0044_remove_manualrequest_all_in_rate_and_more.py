# Generated by Django 4.2.10 on 2024-03-11 23:25

from django.db import migrations, models
import main.apps.oems.models.extensions


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0043_quote_from_currency_quote_to_currency_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='manualrequest',
            name='all_in_rate',
        ),
        migrations.RemoveField(
            model_name='manualrequest',
            name='fee',
        ),
        migrations.RemoveField(
            model_name='manualrequest',
            name='premium',
        ),
        migrations.RemoveField(
            model_name='manualrequest',
            name='rate',
        ),
        migrations.AddField(
            model_name='manualrequest',
            name='booked_all_in_rate',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='manualrequest',
            name='booked_amount',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='manualrequest',
            name='booked_cntr_amount',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='manualrequest',
            name='booked_premium',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='manualrequest',
            name='booked_rate',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='manualrequest',
            name='clearing_broker',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='manualrequest',
            name='exec_broker',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='manualrequest',
            name='far_fixing_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='manualrequest',
            name='far_value_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='manualrequest',
            name='instrument_type',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='manualrequest',
            name='market_name',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='manualrequest',
            name='side',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='manualrequest',
            name='email_status',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='manualrequest',
            name='exec_user',
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
        migrations.AlterField(
            model_name='manualrequest',
            name='expiration_time',
            field=main.apps.oems.models.extensions.DateTimeWithoutTZField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='manualrequest',
            name='fixing_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='manualrequest',
            name='slack_channel',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='manualrequest',
            name='slack_ts',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='manualrequest',
            name='text',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='manualrequest',
            name='time_in_force',
            field=models.CharField(choices=[('15min', '15min')], default='15min', max_length=5),
        ),
        migrations.AlterField(
            model_name='manualrequest',
            name='value_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='manualrequest',
            name='victor_ops_id',
            field=models.CharField(blank=True, null=True),
        ),
    ]
