import logging

from main.libs.pubsub.middleware.interface import MiddlewareInterface


class LoggingMiddleware(MiddlewareInterface):
    """
    A :class:`MiddlewareInterface` that logs all messages.
    """
    def __init__(self):
        self._logger = None

    def setup(self, config, **kwargs):
        self._logger = logging.getLogger(__name__)

    def pre_publish(self, topic, routing_key, data, attrs):
        self._logger.debug(f"Publishing to {topic}#{routing_key}")

    def post_publish_success(self, topic, routing_key, data, attrs):
        self._logger.debug(f"Successfully published to {topic}#{routing_key}")

    def post_publish_failure(self, topic, routing_key, exception, message):
        self._logger.exception(f"Exception raised while publishing message "
                               f"for {topic}: {str(exception.__class__.__name__)}",
                               exc_info = True,
                               extra={"message":message})
