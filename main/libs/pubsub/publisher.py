import abc
import concurrent.futures
import json
import logging
import time
from concurrent.futures import Future

from google.cloud import pubsub_v1
from typing import Union, Dict, List, Any, Type

from main.libs.pubsub.middleware import run_middleware_hook

# Python doesn't have a way to describe serializable objects, this is a workaround type as described in
# Mastering Object-Oriented Python: https://t.ly/0y9g
JSON = Union[Dict[str, Any], List[Any], int, str, float, bool, Type[None]]

_publisher = None  # Should be initialized when you call the init method.
_default_topic_id = None  # Should be initialized when you call the init method.


def publish(routing_key: str, data: 'JSON', blocking=False, timeout=None, raise_exception=True, **attrs):
    """
    Publish a message to the queue under the default topic.

    For full description see :class:`PublisherInterface`
    """
    global _default_topic_id
    try:
        _publisher.publish(_default_topic_id, routing_key, data, blocking, timeout, raise_exception, **attrs)
    except Exception as e:
        logging.error(e)


class PublisherInterface(metaclass=abc.ABCMeta):
    """
    Interface definition for all publisher.
    """

    @classmethod
    def __subclasshook__(cls, subclass):
        return hasattr(subclass, 'publish') and callable(subclass.publish)

    def publish(self, topic, routing_key, data, blocking=False, timeout=None, raise_exception=True, **attrs):
        """
        Publishes message to a queue
        Usage::
            publisher = Publisher()
            publisher.publish('topic_name', 'routing_key', {'foo': 'bar'})

        By default, this method is non-blocking, meaning that the method does not wait for the future to be returned.
        If you would like to wait for the future so you can track the message later, you can:
        Usage::
            publisher = Publisher()
            future = publisher.publish('topic_name', {'foo': 'bar'}, blocking=True, timeout=10.0) # noqa
        However, it should be noted that using `blocking=True` may incur a significant performance hit.

        In addition, the method adds a timestamp `published_at` to the message attrs using
        `epoch floating point number`_.
            .. _epoch floating point number: https://docs.python.org/3/library/time.html#time.time

        Finally, the method takes care of calling the middleware hooks.

        :param topic: string topic to publish the data.
        :param routing_key: string key used to route messages to different consumers.
        :param data: dict with the content of the message.
        :param blocking: boolean
        :param timeout: float, default None falls back to :ref:`settings_publisher_timeout`
        :param raise_exception: boolean. If True, exceptions coming from PubSub will be raised
        :param attrs: additional string parameters to be published.
        :return: A future of the result.
        """

        attrs["published_at"] = str(time.time())
        run_middleware_hook("pre_publish", topic, routing_key, data, attrs)
        payload = json.dumps(data).encode("utf-8")
        future = self._publish(topic, routing_key, payload, **attrs)
        if not blocking:
            return future

        try:
            future.result(timeout=timeout or self.timeout())
        except TimeoutError as e:
            run_middleware_hook("post_publish_failure", topic, e, data)
            if raise_exception:
                raise e
        else:
            run_middleware_hook("post_publish_success", topic, data, attrs)

        return future

    def timeout(self) -> float:
        """
        Default timeout to use. Default value if not implemented is 10.0
        :return: the default time out to use
        """
        return 10.0

    @abc.abstractmethod
    def _publish(self, topic: str, routing_key: str, data: 'JSON', **attrs) -> 'Future':
        """
        Do the actual publishing to the topic.
        :param topic: The topic id
        :param routing_key: The routing key
        :param data: The data to send.
        :param attrs: Additional attributes
        """
        raise NotImplementedError


class NullPubSub(PublisherInterface):
    """
    A :class:`PublisherInterface` implementation that does nothing.
    """

    def _publish(self, topic, routing_key, data, **attrs) -> 'Future':
        f = concurrent.futures.Future()
        f.set_result("")
        return f


class GooglePubSub(PublisherInterface):
    """
     A :class:`PublisherInterface` implementation that publishes to Google Cloud Pub/Sub

     Note that `routing_key` is converted to an attribute and sent to the topic.
    """
    def __init__(self, gc_project_id, credentials):
        self._gc_project_id = gc_project_id
        self._client = pubsub_v1.PublisherClient(credentials=credentials)

    def _publish(self, topic, routing_key, payload, **attrs):
        attrs["routing_key"] = routing_key
        topic_path = self._client.topic_path(self._gc_project_id, topic)
        return self._client.publish(topic_path, payload, **attrs)


def init_google(google_project_id, credentials):
    global _publisher
    _publisher = GooglePubSub(google_project_id, credentials)


def init_null(config):
    global _publisher
    _publisher = NullPubSub()


def set_default_topic_id(topic_id: str):
    global _default_topic_id
    _default_topic_id = topic_id
