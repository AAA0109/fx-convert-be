import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class PriceFeedConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group = "price_feed"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        logger.debug(f"Received message: {message}")
        await self.channel_layer.group_send(
            self.group,
            {"type": "price_feed.tick", "message": message}
        )

    async def quote(self, event):
        message = json.loads(event['message'])
        logger.debug(f"Received quote: {event['message']}")
        await self.send(text_data=json.dumps({"message": message}))
