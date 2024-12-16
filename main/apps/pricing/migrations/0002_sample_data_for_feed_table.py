# Generated by Django 4.2.11 on 2024-04-11 16:37
import json

from django.conf import settings
from django.db import migrations


def forwards_func(apps, schema_editor):
    Feed = apps.get_model('pricing', 'Feed')
    FeedInstrument = apps.get_model('pricing', 'FeedInstrument')
    User = apps.get_model('account', 'User')
    Company = apps.get_model('account', 'Company')

    company = Company.objects.all().first()
    user = User.objects.filter(company=company).first()

    if settings.APP_ENVIRONMENT in ('dev', 'staging'):
        print("Creating sample data for Feed table")
        feed_data = {
            "feed_name": "EXTERNAL1",
            "channel_group": "price_feed",
            "bid_markup": 0.0005,
            "ask_markup": 0.0005,
            "quote_type": "rfq",
            "tick_type": "quote",
            "indicative": True,
            "raw": json.loads('[{"source": "VERTO"}, {"source": "CORPAY"}, {"source": "OER"}]'),
            "user": user,
            "company": company,
        }
        feed, created = Feed.objects.update_or_create(**feed_data)

        instrument_data = {
            "instrument_type": "spot",
            "symbol": "USDJPY",
            "feed": feed,
            "tenors": ["SP", "ON", "TN", "SW", "FW", "2W", "3W", "1M", "2M", "3M"],
        }
        feed, created = FeedInstrument.objects.update_or_create(**instrument_data)


class Migration(migrations.Migration):
    dependencies = [
        ("pricing", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards_func),
    ]
