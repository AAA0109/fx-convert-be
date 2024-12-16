import abc


class MiddlewareInterface(metaclass=abc.ABCMeta):
    """
    Base class for middleware.  The default implementations
       for all hooks are no-ops and subclasses may implement whatever
       subset of hooks they like.
    """
    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'setup') and callable(subclass.setup) and
                hasattr(subclass, 'pre_publish') and callable(subclass.pre_publish) and
                hasattr(subclass, 'post_publish_success') and callable(subclass.post_publish_success) and
                hasattr(subclass, 'post_publish_failure') and callable(subclass.post_publish_failure))

    def setup(self, config, **kwargs):
        """
        Called when middleware is registered.
        :param config: The configuration object
        """
        pass

    def pre_publish(self, topic, routing_key, data, attrs):
        """Called before Publisher sends message.
        :param topic: the topic to publish on
        :param routing_key: the routing key
        :param data: The data being published
        :param attrs: Any additional attributes.
        """
        pass

    def post_publish_success(self, topic, routing_key, data, attrs):
        """Called after Publisher succesfully sends message.
        :param topic: The topic to publish on
        :param routing_key: the routing key
        :param data: The data to publish
        :param attrs: Any additional attributes.
        """
        pass

    def post_publish_failure(self, topic, routing_key, exception, message):
        """Called after publishing fails.
        :param topic: The topic to publish on
        :param routing_key: the routing key
        :param exception: The exception
        :param message: An additional failure message
        """



