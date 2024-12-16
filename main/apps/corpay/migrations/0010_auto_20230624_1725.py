# Generated by Django 3.2.8 on 2023-06-24 17:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0076_alter_cashflow_status'),
        ('corpay', '0009_supportedfxpairs'),
    ]

    operations = [
        migrations.CreateModel(
            name='CorpaySettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('client_code', models.IntegerField()),
                ('signature', models.CharField(max_length=60)),
                ('average_volume', models.IntegerField(default=0)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.company')),
            ],
        ),
        migrations.AlterField(
            model_name='forwardguidelines',
            name='credentials',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='corpay.corpaysettings'),
        ),
        migrations.DeleteModel(
            name='Credentials',
        ),
    ]