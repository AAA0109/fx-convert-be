import json
from abc import ABC
from datetime import datetime

from asgiref.sync import async_to_sync
from django.conf import settings
from hdlib.DateTime.Date import Date

from main.apps.currency.models import FxPair
from main.apps.dataprovider.services.collectors.client import PubSubSubscriber
from main.apps.dataprovider.services.collectors.collector import BaseCollector
from main.apps.dataprovider.services.collectors.quote_tick import QuoteTickFactory, QuoteTick
from main.apps.marketdata.services.fx.fx_provider import CachedFxSpotProvider, FxForwardProvider
from main.apps.oems.backend.order_book import OrderBook
from main.apps.pricing.models import Feed

try:
    # django channels
    from channels.layers import get_channel_layer
except ImportError:
    pass


# ===================

class PriceFeed(ABC):

    def __init__(
        self,
        feed_config: Feed,
        writer=None,
        cache=None,
        publisher=None,
        **kwargs):

        self.config = feed_config
        self.subscriber = PubSubSubscriber()
        self.tick_type = self.config.tick_type
        if kwargs.get("mode", "normal") == "normal":
            self.collector_nm = self.config.collector_name
            self.source = self.config.feed_name
            self.django_channel_group = self.config.channel_group
            self.bid_markup = self.config.raw["bid_markup"]
            self.ask_markup = self.config.raw["ask_markup"]
            self.order_books = {}
            self.check_last = {}
            self.collector = BaseCollector(self.collector_nm, self.source, writer=writer, cache=cache,
                                           publisher=publisher)
            self.factory = QuoteTickFactory(collector=self.collector_nm, source=self.source,
                                            tick_type=self.tick_type, quote_type=self.config.raw["quote_type"],
                                            indicative=self.config.indicative, data_class=QuoteTick)

            if self.django_channel_group:
                self.channel_layer = get_channel_layer()

            # subscribe to feeds
            instruments = self.config.feedinstrument_set.all()
            for source in self.config.raw["source"]:
                for instrument in instruments:
                    # TODO: add tick type to feed_config
                    key = self.subscriber.subscribe_to_tick_feed(self.on_tick, settings.APP_ENVIRONMENT,
                                                                 source, str(instrument),
                                                                 tick_type=self.tick_type)
                    print(source, instrument)

                # TODO: load last from redis... it will be saved in {key}
                # self.populate_check_last(instrument, bid, ask)

    def count_subscriber(self) -> int:
        total_subscriber = 0
        instruments = self.config.feedinstrument_set.all()
        for source in self.config.raw["source"]:
            for instrument in instruments:
                count = self.subscriber.count_subscribers(
                    settings.APP_ENVIRONMENT,
                    source,
                    str(instrument),
                    self.tick_type)

                total_subscriber += count
        return int(total_subscriber)

    def get_order_book(self, instrument):
        if instrument in self.order_books:
            return self.order_books[instrument]
        else:
            ob = OrderBook()
            self.order_books[instrument] = instrument
            return ob

    def check_anti_spam(self, instrument, *args):
        return (instrument in self.check_last and self.check_last[instrument] == args)

    def populate_check_last(self, instrument, *args):
        self.check_last[instrument] = args

    def publish_to_django_channel_group(self, channel_group, msg_type, data):
        # publish message to Django Channels group
        # channel_layer.send, channel_layer.group_send,
        results = async_to_sync(self.channel_layer.group_send)(
            self.django_channel_group,
            {
                "type": msg_type,
                "message": data,
            }
        )
        # do i need to wait here?

    def on_tick(self, message, data, *args, **kwargs):

        # all your price feed logic goes here...
        # to add a new price feed, just make a config and implement this function

        print('RECEIVED:', data)

        bid_time = ask_time = datetime.utcnow()

        instrument = data['instrument']

        # TODO: this might need a lock! with self.locks[instrument]:

        bid = data['bid'] * (1 - self.bid_markup)
        ask = data['ask'] * (1 + self.ask_markup)
        mid = (bid + ask) / 2

        if self.check_anti_spam(instrument, bid, ask):
            return  # anti-spam

        self.populate_check_last(instrument, bid, ask)

        record = self.collector.collect(factory=self.factory,
                                        instrument=instrument,
                                        bid=bid,
                                        bid_time=bid_time,
                                        ask=ask,
                                        ask_time=ask_time,
                                        mid=mid
                                        )

        if record and self.django_channel_group:
            # we should maybe hash this with md5
            channel_group = f'{self.django_channel_group}.{instrument}'
            self.publish_to_django_channel_group(channel_group, self.tick_type, record.export_to_json())

    def run(self, block=True):
        self.subscriber.listen(block=block)


# ===============s

class BboPriceFeed(PriceFeed):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_tick(self, message, data, *args, **kwargs):

        bid_time = ask_time = datetime.utcnow()

        # in this example, self.last is a terrible data structure
        # for order books, use an orderbook data structure (which is a priority queue)
        # HF firms compute lots of various AI features about the order book (steepness, volume, zscore spread, etc.)
        #
        instrument = data['instrument']

        # TODO: this might need a lock! with self.locks[instrument]:
        ob = self.get_order_book(instrument)

        if isinstance(data['bid'], float):
            ob.store_bid(data['source'], data['bid'], data['bid_size'], bid_time)

        if isinstance(data['ask'], float):
            ob.store_ask(data['source'], data['ask'], data['ask_size'], bid_time)

        best_bid, best_ask = ob.bbo()

        if self.check_anti_spam(instrument, best_bid, best_ask):
            return  # anti-spam

        self.populate_check_last(instrument, best_bid, best_ask)

        best_bid *= (1 - self.bid_markup)
        best_ask *= (1 + self.ask_markup)
        mid = (best_bid + best_ask) / 2

        record = self.collector.collect(factory=self.factory,
                                        instrument=instrument,
                                        bid=best_bid,
                                        bid_time=bid_time,
                                        ask=best_ask,
                                        ask_time=ask_time,
                                        mid=mid
                                        )

        if record and self.django_channel_group:
            self.publish_to_django_channel_group(self.tick_type, record)


class ExamplePriceFeed(PriceFeed):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_tick(self, message, data, *args, **kwargs):
        print('RECEIVED:', data)

        # Decode the bytestring to a string
        decoded_data = data.decode("utf-8")

        # Load the string as a dictionary
        data = json.loads(decoded_data)

        # in this example, self.last is a terrible data structure
        # for order books, use an orderbook data structure (which is a priority queue)
        # HF firms compute lots of various AI features about the order book (steepness, volume, zscore spread, etc.)

        bid_time = ask_time = datetime.utcnow()
        instrument = data['instrument']
        bid = data['bid']
        ask = data['ask']

        if self.check_anti_spam(instrument, bid, ask):
            return  # anti-spam

        self.populate_check_last(instrument, bid, ask)

        bid_product_markup = 0.05
        ask_product_markup = 0.05
        risk_markup = 0.05
        credit_markup = 0.05

        # broker markup
        bid_broker_fee = self._broker_markup(bid, self.bid_markup)
        ask_broker_fee = self._broker_markup(ask, self.ask_markup)
        # product markup
        bid_product_fee = self._product_markup(bid, bid_product_markup)
        ask_product_fee = self._product_markup(ask, ask_product_markup)
        # customer markup
        bid_customer_fee = self._customer_markup(bid, risk_markup, credit_markup)
        ask_customer_fee = self._customer_markup(ask, risk_markup, credit_markup)

        spot_provider = CachedFxSpotProvider()
        fwd_provider = FxForwardProvider(fx_spot_provider=spot_provider)

        pair = FxPair.get_pair(instrument.split("-")[0])
        value_date = Date.from_int(self.config.raw["value_date"])

        tenors = ['SN', '1W', '2W', '3W', '1M', '2M', '3M', '4M', '5M', '6M', '9M', '1Y']
        curve = fwd_provider.get_forward_bid_ask_curve(pair=pair, tenors=tenors)
        fwd_points = curve.points_at_D(value_date)
        spread_points = curve.spread_at_D(value_date)
        fwd_points_bid = fwd_points - (spread_points / 2)
        fwd_points_ask = fwd_points + (spread_points / 2)
        print('mid', fwd_points, 'bid', fwd_points_bid, 'ask', fwd_points_ask)

        # composite fees
        total_bid_fee = bid_broker_fee + bid_product_fee + bid_customer_fee
        total_ask_fee = ask_broker_fee + ask_product_fee + ask_customer_fee

        bid = bid + fwd_points_bid - total_bid_fee
        ask = ask + fwd_points_ask + total_ask_fee
        mid = (bid + ask) / 2

        record = self.collector.collect(factory=self.factory,
                                        instrument=instrument,
                                        bid=bid,
                                        bid_time=bid_time,
                                        ask=ask,
                                        ask_time=ask_time,
                                        mid=mid
                                        )

        if record and self.django_channel_group:
            channel_group = f'{self.django_channel_group}.{instrument}'
            self.publish_to_django_channel_group(channel_group, self.tick_type, record.export_to_json())

    # ============== Private Methods ==============

    @staticmethod
    def _broker_markup(rate, markup) -> float:
        return rate * markup

    @staticmethod
    def _product_markup(rate, markup):
        """
        Applies product/feature markup based on selected features.
        """
        return rate * markup

    @staticmethod
    def _customer_markup(rate, risk, creditworthiness):
        """
        Adjusts the rate based on the customer's risk and creditworthiness.
        """
        return rate * risk * creditworthiness


class PriceFeedFactory:
    @staticmethod
    def create_price_feed(feed_id: int, *args, **kwargs) -> PriceFeed:
        """
        Factory method to create different types of price feeds.

        :param feed_id: The primary key of the Feed model.
        :param args: Additional arguments to pass to the PriceFeed constructor.
        :param kwargs: Additional keyword arguments to pass to the PriceFeed constructor.
        :return: An instance of a PriceFeed subclass.
        """
        feed_config = Feed.objects.get(id=feed_id)
        if feed_config.feed_type == 'bbo':
            model_class = BboPriceFeed
        elif feed_config.feed_type == 'example':
            model_class = ExamplePriceFeed
        elif feed_config.feed_type == 'default':
            model_class = PriceFeed
        else:
            raise ValueError(f"Unknown feed type: {feed_config.feed_type}")
        return model_class(feed_config=feed_config, *args, **kwargs)


if __name__ == "__main__":
    instruments = ['USDJPY-SPOT']

    # this config should be a version-controlled yaml file or in the database
    # I always loved s3 because you get version control on object storage
    # so you can always look to see what the feed config looks like throughout history
    feed_config = {
        'django_channel_group': 'price_feed',
        'name': 'EXTERNAL1',
        'bid_markup': 0.0005,
        'ask_markup': 0.0005,
        'quote_type': 'rfq',
        'tick_type': 'quote',
        'indicative': True,
        'raw': ([
            {'source': 'VERTO'},
            {'source': 'CORPAY'},
            {'source': 'OER'},
        ])
    }

    external_feed1 = PriceFeed('DEV1', feed_config)
    external_feed1.run()

    """
    # =====================================
    # ^^^ this price feed is saving into redis the last update and pushing over the network

    # we can use websocketd to stream this price into a websocket client

    company-<user>:
        USDJPY-SPOT: EXTERNAL1
        USDJPY-1M: EXTERNAL1
        EURUSD-SPOT: EXTERNAL2
        DEFAULT:

    pangea-<user>:
        USDJPY-SPOT: BBO_INTERNAL1 # Best-bid-offer

    # new django endpoint - quote (takes instrument USDJPY-SPOT, company, user?)
    # if quote is USDJPY-2024/04/16,
        pull SPOT and then lookup in the spot config what the default source of fwd points is, and calculate the fwd points
        to <value-date> and return latest_spot + fwd_points_at_value_date

    # if quote is USDJPY-1M
        # check that this feed_config exists otherwise use default or raise error for now

    # this endpoint looks up the price feed for the configuration and returns last.
    # eventually, we could look up data in big query and return a time-series for analytics
    """
