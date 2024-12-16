# Generated by Django 3.2.8 on 2023-02-06 07:53

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


def migrate_data_to_new_table(apps, schema_editor):
    DepositFundsResponse = apps.get_model("ibkr", "DepositFundsResponse")
    DepositResult = apps.get_model("ibkr", "DepositResult")
    for obj in DepositFundsResponse.objects.all():
        DepositResult.objects.create(
            ib_instr_id=obj.ib_instr_id,
            code=obj.code,
            description=obj.description,
            amount=obj.amount,
            method=obj.method,
            currency=obj.currency,
            funding_request=obj.funding_request
        )


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0002_auto_20220702_1908'),
        ('ibkr', '0021_auto_20230109_0120'),
    ]

    operations = [
        migrations.CreateModel(
            name='DepositResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('ib_instr_id', models.IntegerField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processed', 'Processed'), ('rejected', 'Rejected')], default='pending', max_length=11)),
                ('code', models.CharField(blank=True, max_length=255, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('amount', models.FloatField(blank=True, null=True)),
                ('method', models.CharField(blank=True, max_length=10, null=True)),
                ('saved_instruction_name', models.CharField(blank=True, max_length=60, null=True)),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.currency')),
                ('funding_request', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='deposit_result', to='ibkr.fundingrequest')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FundingRequestResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('ib_instr_id', models.IntegerField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processed', 'Processed'), ('rejected', 'Rejected')], default='pending', max_length=11)),
                ('code', models.CharField(blank=True, max_length=255, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('funding_request', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='result', to='ibkr.fundingrequest')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='WithdrawResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('ib_instr_id', models.IntegerField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processed', 'Processed'), ('rejected', 'Rejected')], default='pending', max_length=11)),
                ('code', models.CharField(blank=True, max_length=255, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('amount', models.FloatField(blank=True, null=True)),
                ('method', models.CharField(blank=True, max_length=10, null=True)),
                ('saved_instruction_name', models.CharField(blank=True, max_length=60, null=True)),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.currency')),
                ('funding_request', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='withdraw_result', to='ibkr.fundingrequest')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterField(
            model_name='fundingrequestprocessingstat',
            name='funding_request',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='processing_stat', to='ibkr.fundingrequest'),
        ),
        migrations.AlterField(
            model_name='fundingrequeststatus',
            name='funding_request',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='status', to='ibkr.fundingrequest'),
        ),
        migrations.RunPython(migrate_data_to_new_table),
        migrations.DeleteModel(
            name='DepositFundsResponse',
        ),
    ]
