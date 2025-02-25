# Generated by Django 4.2.3 on 2024-01-29 12:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0006_order_orderevent_quote_waitcondition_orderqueue_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderevent',
            name='order',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='order_orderevent', to='oems.order'),
        ),
        migrations.AddField(
            model_name='orderevent',
            name='quote',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='quote_orderevent', to='oems.quote'),
        ),
        migrations.AddField(
            model_name='orderevent',
            name='request_data',
            field=models.JSONField(null=True),
        ),
        migrations.AddField(
            model_name='orderevent',
            name='response_data',
            field=models.JSONField(null=True),
        ),
    ]
