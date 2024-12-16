# Generated by Django 3.2.8 on 2022-06-23 00:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0017_alter_cashflow_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cashflow',
            name='status',
            field=models.TextField(choices=[('inactive', 'INACTIVE'), ('draft', 'DRAFT'), ('pending_activation', 'PENDING ACTIVATION'), ('active', 'ACTIVE'), ('pending_deactivation', 'PENDING_DEACTIVATION')], default='draft'),
        ),
    ]