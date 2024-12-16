import json

from google.cloud import pubsub_v1

# Configuration
project_id = "pangea-development"
topic_id = "dev.VERTO_USDJPY-SPOT_quote"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_id)


def publish_message(data):
    """Publishes a message to a Pub/Sub topic."""
    # Data must be a bytestring
    data = json.dumps(data).encode("utf-8")
    future = publisher.publish(topic_path, data)
    print(f"Published message ID: {future.result()}")


data = {
    "instrument": "USDJPY-SPOT",
    "bid": 104.75,
    "ask": 104.77,
    "source": "VERTO",
    "bid_size": 5,
    "ask_size": 5,
}

publish_message(data)
