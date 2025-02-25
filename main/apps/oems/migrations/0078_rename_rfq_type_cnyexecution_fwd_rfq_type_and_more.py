# Generated by Django 4.2.11 on 2024-05-13 15:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0077_alter_ticket_payment_memo'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cnyexecution',
            old_name='rfq_type',
            new_name='fwd_rfq_type',
        ),
        migrations.AddField(
            model_name='cnyexecution',
            name='spot_rfq_type',
            field=models.CharField(choices=[('api', 'API'), ('manual', 'MANUAL'), ('unsupported', 'UNSUPPORTED'), ('indicative', 'INDICATIVE'), ('norfq', 'NORFQ')], default='unsupported', max_length=16),
        ),
    ]
