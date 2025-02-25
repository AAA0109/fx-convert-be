# Generated by Django 4.2.10 on 2024-02-21 21:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0018_alter_ticket_eid_alter_ticket_execution_strategy_and_more'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='ticket',
            name='oems_ticket_eid_4a263d_idx',
        ),
        migrations.RenameField(
            model_name='ticket',
            old_name='eid',
            new_name='ticket_id',
        ),
        migrations.AlterField(
            model_name='ticket',
            name='value_date',
            field=models.DateField(help_text='The date when the transaction value will be settled. Defaults to next business day if non-settlement day.'),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['ticket_id'], name='oems_ticket_ticket__d55923_idx'),
        ),
    ]
