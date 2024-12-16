# Generated by Django 4.2.10 on 2024-03-12 19:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0044_remove_manualrequest_all_in_rate_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='manualrequest',
            name='action',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='manualrequest',
            name='ref_rate',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='manualrequest',
            name='amount',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='manualrequest',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('expired', 'Expired'), ('complete', 'Complete'), ('canceled', 'Canceled')], default='pending', max_length=8),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='quote_type',
            field=models.CharField(blank=True, choices=[('api', 'API'), ('manual', 'MANUAL'), ('unsupported', 'UNSUPPORTED'), ('indicative', 'INDICATIVE'), ('norfq', 'NORFQ')], max_length=16, null=True),
        ),
    ]
