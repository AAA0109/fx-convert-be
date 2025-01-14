# Generated by Django 4.2.11 on 2024-05-22 17:05

from django.db import migrations


def create_cashflow_tickets_relation(apps, schema_editor):
    SingleCashFlow = apps.get_model('cashflow', 'SingleCashFlow')
    Ticket = apps.get_model('oems', 'Ticket')

    for cashflow in SingleCashFlow.objects.all():
        if cashflow.ticket_id:
            try:
                ticket = Ticket.objects.get(ticket_id=cashflow.ticket_id)
                cashflow.tickets.add(ticket)
            except Ticket.DoesNotExist:
                continue


class Migration(migrations.Migration):
    dependencies = [
        ('cashflow', '0019_singlecashflow_tickets'),
    ]

    operations = [
        migrations.RunPython(create_cashflow_tickets_relation),
    ]
