# Generated by Django 3.2.8 on 2022-09-18 08:53

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('ibkr', '0007_fundingrequestprocessingstats_trans_understood'),
    ]

    operations = [
        migrations.CreateModel(
            name='FundingRequestProcessingStat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('instruction_set_id', models.IntegerField(blank=True, null=True)),
                ('trans_read', models.IntegerField(blank=True, null=True)),
                ('trans_understood', models.IntegerField(blank=True, null=True)),
                ('trans_provided', models.IntegerField(blank=True, null=True)),
                ('trans_rejected', models.IntegerField(blank=True, null=True)),
                ('funding_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='funding_request_processing_stats', to='ibkr.fundingrequest')),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.AlterField(
            model_name='depositfundsresponse',
            name='funding_request',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deposit_funds_responses', to='ibkr.fundingrequest'),
        ),
        migrations.AlterField(
            model_name='fundingrequeststatus',
            name='funding_request',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='funding_request_statuses', to='ibkr.fundingrequest'),
        ),
        migrations.DeleteModel(
            name='FundingRequestProcessingStats',
        ),
    ]
