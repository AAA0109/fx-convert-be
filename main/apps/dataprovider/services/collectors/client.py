import json
import threading
import traceback
import uuid
from concurrent.futures import TimeoutError
from datetime import date, timedelta

from django.conf import settings
from google.api_core.exceptions import NotFound
from google.cloud import pubsub_v1
from google.protobuf import duration_pb2


# ===========

class PubSubSubscriber:

    def __init__(self, project_id=settings.GCP_PROJECT_ID, env=settings.APP_ENVIRONMENT, ack_deadline_seconds=10, ):

        self.project_id = project_id
        self.env = env
        self.subscriber = pubsub_v1.SubscriberClient()
        self.topics = set()
        self.subscriptions = {}
        # self.callbacks = defaultdict(list)
        self.future_subscriptions = {}
        self.threads = {}
        self.kill_sig = False
        self.ack_deadline_seconds = ack_deadline_seconds

        self.message_retention_duration = duration_pb2.Duration()
        self.message_retention_duration.FromSeconds(10 * 60)  # 10m, minimum

        self.expiration_policy = pubsub_v1.types.ExpirationPolicy()
        self.expiration_policy.ttl = timedelta(hours=24)

    def add_subscription(self, topic_name, subscription_name=None, callback=None, unique=True):

        if topic_name in self.topics:
            raise ValueError

        if subscription_name is None:
            # Generate a unique subscription name if not provided
            if unique:
                subscription_name = f"{self.env}-{date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex}"
            else:
                subscription_name = f"{topic_name}"

        topic_path = self.subscriber.topic_path(self.project_id, topic_name)
        subscription_path = self.subscriber.subscription_path(self.project_id, subscription_name)

        try:
            self.subscriber.create_subscription(
                request={
                    "name": subscription_path,
                    "topic": topic_path,
                    "ack_deadline_seconds": self.ack_deadline_seconds,
                    "message_retention_duration": self.message_retention_duration,
                    "expiration_policy": self.expiration_policy,
                }
            )
            print(f"Subscription {subscription_name} to topic {topic_name} created.")
            self.subscriptions[subscription_name] = (subscription_path, callback)
            self.topics.add(topic_name)
            # if callable(callback): self.callbacks[topic_name].append(callback)
        except Exception as e:
            print(f"ERROR: Could not create subscription {subscription_name}: {e}")

    def delete_subscription(self, subscription_name):
        if subscription_name in self.subscriptions:
            subscription_path, _ = self.subscriptions[subscription_name]
            try:
                self.subscriber.delete_subscription(subscription=subscription_path)
            except:
                pass
            print(f"Subscription {subscription_name} deleted.")
            del self.subscriptions[subscription_name]
        else:
            print(f"Subscription {subscription_name} not found.")

    def close(self):

        for subscription_name, subscription in self.subscriptions.items():
            try:
                self.subscriber.delete_subscription(subscription=subscription[0])
            except:
                traceback.print_exc()

        for subscription_name, thread in self.threads.items():
            self.stop_listening(subscription_name)

        # for thread in self.threads.values():
        #    thread._stop()

        # self.subscriptions.clear()
        # self.future_subscriptions.clear()

    def callback(self, message, data):
        print("Data:", data)

    @staticmethod
    def parse_message(message):
        if 'content_type' in message.attributes:
            if message.attributes['content_type'] == 'json':
                try:
                    data = json.loads(message.data)
                except Exception as e:
                    print(e)
                    data = message.data
                return data
        return message.data

    def wrap_callback(self, callback):
        def wrapped_callback(message):
            # print(f"Received message: {message}")
            message.ack()
            # print('acked message')
            data = self.parse_message(message)
            callback(message, data)
            # print("After callback")

        return wrapped_callback

    # ==============================================

    def listen_for_messages(self, subscription_name, timeout=None):

        if subscription_name not in self.subscriptions:
            print(f"Subscription {subscription_name} not found.")
            return

        if subscription_name in self.future_subscriptions:
            streaming_pull_future = self.future_subscriptions[subscription_name]
        else:
            subscription_path, callback = self.subscriptions[subscription_name]
            streaming_pull_future = self.subscriber.subscribe(subscription_path, callback=self.wrap_callback(callback))
            self.future_subscriptions[subscription_name] = streaming_pull_future

        def _inner_listen():
            print(f"Listening for messages on {subscription_name}...")

            if timeout is not None:
                try:
                    streaming_pull_future.result(timeout=timeout)
                except TimeoutError:
                    streaming_pull_future.cancel()
                    streaming_pull_future.result()
                except Exception as e:
                    streaming_pull_future.cancel()
                    print(f"Listening for messages on {subscription_name} stopped with error: {e}")
            else:
                try:
                    streaming_pull_future.result(timeout=timeout)
                except TimeoutError:
                    streaming_pull_future.cancel()
                    streaming_pull_future.result()
                except Exception as e:
                    streaming_pull_future.cancel()
                    print(f"Listening for messages on {subscription_name} stopped with error: {e}")

        thread = threading.Thread(target=_inner_listen)
        self.threads[subscription_name] = thread
        thread.start()

    # ==================

    def listen(self, timeout=None, block=True):
        for subscription_name in self.subscriptions.keys():
            self.listen_for_messages(subscription_name)
        if block and self.subscriptions:
            # self.threads[subscription_name].join()
            import time
            try:
                while True:
                    time.sleep(0.0001)
            except KeyboardInterrupt:
                pass
            finally:
                self.close()

    def stop_listening(self, subscription_name):
        if subscription_name in self.future_subscriptions:
            future = self.future_subscriptions[subscription_name]
            future.cancel()
            # self.threads[subscription_name].join()
            print(f"Stopped listening to {subscription_name}.")
        else:
            print(f"No active listening found for {subscription_name}.")

    # ==================

    def subscribe_to_tick_feed(self, callback, tgt_env, source, instrument, tick_type='quote'):
        topic = f"{tgt_env}.{source}_{instrument}_{tick_type}"
        self.add_subscription(topic, callback=callback)
        return topic

    def count_subscribers(self, tgt_env, source, instrument, tick_type='quote'):
        """Counts the number of subscribers for a given topic."""
        topic_name = f"{tgt_env}.{source}_{instrument}_{tick_type}"
        topic_path = self.subscriber.topic_path(self.project_id, topic_name)
        try:
            # Fetch all subscriptions for the topic
            subscription_iterator = self.subscriber.list_subscriptions(
                request={"project": f"projects/{self.project_id}"})
            # Count subscriptions that are subscribed to the topic
            count = sum(1 for sub in subscription_iterator if sub.topic == topic_path)
            print(f"Number of subscribers for topic {topic_name}: {count}")
            return count
        except NotFound:
            print(f"Topic {topic_name} not found.")
            return 0


# ==================

if __name__ == "__main__":
    client = PubSubSubscriber()

    client.subscribe_to_tick_feed(client.callback, 'dev', 'VERTO', 'USDCAD-SPOT')
    client.subscribe_to_tick_feed(client.callback, 'dev', 'CORPAY', 'USDJPY-SPOT')
    client.subscribe_to_tick_feed(client.callback, 'dev', 'OER', 'USDPLN-SPOT')

    client.listen()
