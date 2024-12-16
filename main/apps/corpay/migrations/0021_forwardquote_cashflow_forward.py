# Generated by Django 4.2 on 2023-08-25 00:55

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0078_alter_cashflow_currency_alter_draftcashflow_currency'),
        ('corpay', '0020_merge_20230815_1542'),
    ]

    operations = [
        migrations.AddField(
            model_name='forwardquote',
            name='cashflow',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='quote_cashflow', to='account.cashflow'),
        ),
        migrations.CreateModel(
            name='Forward',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('corpay_forward_id', models.IntegerField()),
                ('order_number', models.TextField()),
                ('token', models.TextField()),
                ('forward_quote', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='corpay.forwardquote')),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
    ]