# Generated by Django 4.2.15 on 2024-10-09 07:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0106_ticket_settlement_attempt'),
    ]

    operations = [
        migrations.AlterField(
            model_name='waitcondition',
            name='quote',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='wait_condition_quote', to='oems.quote'),
        ),
    ]