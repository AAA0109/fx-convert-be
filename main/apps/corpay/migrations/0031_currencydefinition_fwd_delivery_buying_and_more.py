# Generated by Django 4.2.3 on 2023-10-22 10:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('corpay', '0030_onboarding_onboardingfile'),
    ]

    operations = [
        migrations.AddField(
            model_name='currencydefinition',
            name='fwd_delivery_buying',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='currencydefinition',
            name='fwd_delivery_selling',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='currencydefinition',
            name='incoming_payments',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='currencydefinition',
            name='outgoing_payments',
            field=models.BooleanField(default=False),
        ),
    ]
