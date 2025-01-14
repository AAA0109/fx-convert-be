# Generated by Django 4.2.10 on 2024-02-20 22:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0012_ticket_external_quote_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticket',
            name='execution_strategy',
            field=models.CharField(blank=True, choices=[('market', 'Market'), ('strategic_execution', 'Strategic Execution'), ('smart', 'SMART'), ('bestx', 'BESTX')], max_length=128, null=True),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='internal_quote_id',
            field=models.TextField(blank=True, null=True),
        ),
    ]
