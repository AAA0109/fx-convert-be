from django.urls import re_path

from main.apps.dataprovider.api.consumers.price_feed import PriceFeedConsumer

websocket_urlpatterns = [
    re_path(r"ws/price_feed/", PriceFeedConsumer.as_asgi())
]
