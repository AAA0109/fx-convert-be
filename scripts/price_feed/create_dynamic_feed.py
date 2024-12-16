import os
import sys

if __name__ == "__main__":
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")
    import django

    django.setup()
    from main.apps.fee.models import Feed, FeedInstrument

    input_string = "EXTERNAL1 :: USDJPY-20240426"

    feed_name, data = input_string.split(" :: ")

    currency = data[:-8]  # 'USDJPY'
    date = data[-8:]  # '20240426'

    formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:]}"

    print(feed_name)  # 'EXTERNAL1'
    print(currency)  # 'USDJPY'
    print(formatted_date)  # '2024-04-26'

    feed, updated = Feed.objects.update_or_create(
        tag=tag,
        user_id=1,
        company_id=1,
        defaults={
            'indicative': True,
            'raw': {"source": ["VERTO", "CORPAY", "OER"],
                    "ask_markup": 0.0005,
                    "bid_markup": 0.0005,
                    "quote_type": "rfq",
                    "value_date": 20240514,
                    "fwd_point_src": "ICE,EOD"},
            'enabled': True},
        ...
    )

    instrument_data = {
        "instrument_type": "spot",
        "symbol": currency,
        "feed": feed,
        "tenors": [],
    }
    feed_instrument, created = FeedInstrument.objects.get_or_create(**instrument_data)
