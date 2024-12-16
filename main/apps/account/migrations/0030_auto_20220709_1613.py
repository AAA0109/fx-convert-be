# Generated by Django 3.2.8 on 2022-07-09 16:13

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0002_auto_20220702_1908'),
        ('account', '0029_cashflow_roll_convention'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cashflow',
            name='currency',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cashflow_currency', to='currency.currency'),
        ),
        migrations.AlterField(
            model_name='cashflow',
            name='status',
            field=models.CharField(choices=[('inactive', 'INACTIVE'), ('pending_activation', 'PENDING ACTIVATION'), ('active', 'ACTIVE'), ('pending_deactivation', 'PENDING_DEACTIVATION')], default='pending_activation', max_length=24),
        ),
        migrations.CreateModel(
            name='DraftCashFlow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('date', models.DateField()),
                ('amount', models.FloatField()),
                ('name', models.CharField(max_length=60, null=True)),
                ('description', models.TextField(null=True)),
                ('periodicity', models.TextField(blank=True, null=True)),
                ('calendar', models.CharField(blank=True, choices=[('inactive', 'INACTIVE'), ('NULL_CALENDAR', 'NULL_CALENDAR'), ('WESTERN_CALENDAR', 'WESTERN_CALENDAR')], default='NULL_CALENDAR', max_length=64, null=True)),
                ('roll_convention', models.CharField(blank=True, choices=[('UNADJUSTED', 'Unadjusted'), ('FOLLOWING', 'Following'), ('MODIFIED_FOLLOWING', 'Modified Following'), ('HALF_MONTH_MODIFIED_FOLLOWING', 'Half Month Modified Following'), ('PRECEDING', 'Preceding'), ('MODIFIED_PRECEDING', 'Modified Preceding'), ('NEAREST', 'Nearest')], default='UNADJUSTED', max_length=64, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='draft_company', to='account.company')),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='draftcashflow_currency', to='currency.currency')),
            ],
            options={
                'verbose_name_plural': 'drafts',
            },
        ),
        migrations.AddField(
            model_name='cashflow',
            name='draft',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cf_draft', to='account.draftcashflow'),
        ),
    ]