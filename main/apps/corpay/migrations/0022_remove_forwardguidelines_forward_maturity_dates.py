# Generated by Django 4.2 on 2023-08-25 03:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('corpay', '0021_forwardquote_cashflow_forward'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='forwardguidelines',
            name='forward_maturity_dates',
        ),
    ]