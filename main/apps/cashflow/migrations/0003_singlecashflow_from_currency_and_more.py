# Generated by Django 4.2.10 on 2024-02-29 00:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0019_deliverytime'),
        ('cashflow', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='singlecashflow',
            name='from_currency',
            field=models.ForeignKey(help_text='The from currency of the cashflow', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_from_currency', to='currency.currency'),
        ),
        migrations.AddField(
            model_name='singlecashflow',
            name='self_directed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='singlecashflow',
            name='to_currency',
            field=models.ForeignKey(help_text='The to currency of the cashflow', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_to_currency', to='currency.currency'),
        ),
    ]
