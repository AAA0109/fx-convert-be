# Generated by Django 4.2.11 on 2024-04-22 19:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0071_ticket_commission_ticket_commission_ccy_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticket',
            name='funding',
            field=models.CharField(blank=True, default='postfunded', help_text='Specifies the ticket funding type.', max_length=32, null=True, verbose_name=[('prefunded', 'prefunded'), ('postfunded', 'postfunded'), ('premargined', 'premargined'), ('postmargined', 'postmargined'), ('flexible', 'flexible')]),
        ),
    ]
