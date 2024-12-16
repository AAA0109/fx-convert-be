import logging
import traceback
from typing import Any, List, Optional

from cachetools import LRUCache

from django.conf import settings
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from celery import shared_task

# This handler does retries when HTTP status 429 is returned
from slack_sdk.http_retry.builtin_handlers import RateLimitErrorRetryHandler
from slack_sdk.signature import SignatureVerifier

def decorator_to_post_exception_message_on_slack(channel: str = None):
    """
    A decorator to send exception notifications to a Slack channel using the Slack API.

    Attributes:
        channel (str): The Slack channel to post the exception using the Slack API.
    """

    def inner(func):
        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except Exception as ex:
                _channel: str = f"{settings.APP_ENVIRONMENT}-{channel}" if channel \
                    else settings.SLACK_NOTIFICATIONS_CHANNEL
                logging.info(f"Slack exception notification to be posted on {_channel}")
                slack = SlackNotification()
                parent_ts = slack.send_text_message(
                    channel=_channel,
                    text=f":warning: {ex.__str__()}"
                )
                child_ts = slack.send_mrkdwn_message(
                    text=":warning:",
                    channel=_channel,
                    mrkdwn=f"""```{traceback.format_exc()}```""",
                    thread_ts=parent_ts
                )
                raise ex

        return wrapper

    return inner


def send_exception_to_slack(message: str, key = None, channel: str = None, log_level='error'):
    if not hasattr(send_exception_to_slack, 'antispam'):
        send_exception_to_slack.antispam = LRUCache(256)
    _channel: str = f"{settings.APP_ENVIRONMENT}-{channel}" if channel \
                    else settings.SLACK_NOTIFICATIONS_CHANNEL
    if not _channel:
        return

    if not isinstance(message, str):
        except_type = message.__str__()
    else:
        except_type = 'n/a'

    spam_key = (_channel, except_type, key or message)
    if spam_key in send_exception_to_slack.antispam:
        return
    send_exception_to_slack.antispam[spam_key] = True

    if isinstance(message, str):
        parent_txt = f":warning: {settings.APP_ENVIRONMENT} {log_level}"
        child_txt = f"""```{message}\n\n{traceback.format_exc()}```"""
    else:
        try:
            parent_txt = f":warning: {settings.APP_ENVIRONMENT} {except_type}"
            child_txt = f"""```{traceback.format_exc()}```"""
        except:
            return

    logging.info(f"Slack exception notification to be posted on {_channel}")

    try:
        slack = SlackNotification()
        parent_ts = slack.send_text_message(
            channel=_channel,
            text=parent_txt
        )
        child_ts = slack.send_mrkdwn_message(
            text=":warning:",
            channel=_channel,
            mrkdwn=child_txt,
            thread_ts=parent_ts
        )
    except:
        logging.debug(f"Slack exception notification failed on {_channel}")

    return

# @shared_task(bind=True, time_limit=30 * 60, max_retries=1)
def send_message_to_slack(message: str, child_message: str = None, channel: str = None):

    _channel: str = channel or settings.SLACK_NOTIFICATIONS_CHANNEL
    if not _channel:
        return

    logging.info(f"Slack message notification to be posted on {_channel}")

    try:
        slack = SlackNotification()
        parent_ts = slack.send_text_message(
            text=message,
            channel=_channel,
        )
        if child_message:
            child_ts = slack.send_text_message(
                text=child_message,
                channel=_channel,
                thread_ts=parent_ts
            )
    except:
        logging.debug(f"Slack exception notification failed on {_channel}")
        traceback.print_exc()

    return

class SlackNotification:
    """
    A class to send notifications to a Slack channel using the Slack API.

    Attributes:
        client (WebClient): The WebClient instance used to interact with the Slack API.
    """

    client: WebClient

    def __init__(self, verify=False):
        """
        Initialize the SlackNotification class with a new WebClient instance.
        """
        self.client = WebClient(
            token=settings.SLACK_NOTIFICATIONS_APP_BOT_TOKEN
        )
        rate_limit_handler = RateLimitErrorRetryHandler(max_retry_count=1)
        self.client.retry_handlers.append(rate_limit_handler)
        if verify: self.signature_verifier = SignatureVerifier(settings.SLACK_SIGNING_SECRET)

    def delete_message(self, channel: str = None, thread_ts: str = None) -> None:
        try:
            response = self.client.chat_delete(
                channel=channel,
                ts=thread_ts
            )
            return response.data
        except SlackApiError as e:
            print(f"Error deleting message: {e}")

    def edit_message(
        self,
        channel: str = None,
        text: str = None,
        blocks: List = None,
        thread_ts: str = None
    ) -> None:

        try:
            response = self.client.chat_update(
                channel=channel,
                ts=thread_ts,
                text=text,
                blocks=blocks,
            )
            return response.data
        except SlackApiError as e:
            print(f"Error updating message: {e}")

    def send_blocks(
            self,
            channel: str = None,
            text: str = None,
            blocks: List = None,
            thread_ts: str = None,
            return_data: bool = False,
        ) -> str:
        """
        Post a message to a Slack channel using the Slack API.

        Args:
            channel (str): The ID of the Slack channel to post the message to.
            text (str): The text of the message to post.
            blocks (List): The blocks of the message to post.
            thread_ts (str): The timestamp of the parent message, if posting a threaded message.

        Returns:
            str: The timestamp of the newly created message.
        """
        response = self.client.chat_postMessage(
            channel=channel if channel else settings.SLACK_NOTIFICATIONS_CHANNEL,
            text=text,
            blocks=blocks,
            thread_ts=thread_ts
        )

        if response.status_code == 200 and response.data.get('ok'):
            thread_ts = response.data.get('ts')
            logging.info(f"Slack notification posted successfully. Thread timestamp: {thread_ts}")
            if return_data: return response.data
        else:
            logging.error(f"Slack notification failed with status code {response.status_code}")
            raise Exception(f"Slack notification failed with status code {response.status_code}")
        return thread_ts

    def send_text_message(
        self,
        text: str,
        is_header: bool = False,
        channel: str = None,
        thread_ts: str = None
    ) -> str:
        """
        Send a text message to a Slack channel using the Slack API.

        Args:
            text (str): The text of the message to send.
            is_header (bool): Whether the message should be formatted as a header.
            channel (str): The ID of the Slack channel to send the message to.
            thread_ts (str): The timestamp of the parent message, if sending a threaded message.

        Returns:
            str: The timestamp of the newly created message.
        """
        logging.info(f"Sending text message to Slack channel.")
        blocks = [
            {
                "type": "header" if is_header else "section",
                "text": {
                    "type": "plain_text",
                    "text": text,
                }
            }
        ]
        return self.send_blocks(
            text=text,
            channel=channel,
            blocks=blocks,
            thread_ts=thread_ts
        )

    def send_mrkdwn_message(
        self,
        mrkdwn: str,
        text: str = None,
        channel: str = None,
        thread_ts: str = None
    ) -> Any:
        """
        Sends a message to a Slack channel with the specified markdown-formatted text.

        Args:
            mrkdwn (str): The markdown-formatted text to send.
            text (str, optional): The text to display as a header above the message.
                                  Defaults to None.
            channel (str, optional): The ID of the Slack channel to send the message to.
                                     If not provided, the default channel specified in settings is used.
                                     Defaults to None.
            thread_ts (str, optional): The timestamp of the parent message to thread this message under.
                                        If not provided, the message will not be threaded.
                                        Defaults to None.

        Returns:
            Any: The response from the Slack API.

        Raises:
            Exception: If the Slack API returns an error.
        """
        logging.info(f"Sending a markdown-formatted message to Slack.")

        # Format the message as a Slack block with the specified markdown text
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{mrkdwn}"
                }
            },
        ]

        # Send the message using the _post_on_slack() method
        return self.send_blocks(
            text=text,
            channel=channel,
            blocks=blocks,
            thread_ts=thread_ts
        )

    def get_permalink(self, channel: str = None, thread_ts: str = None) -> Optional[dict]:
        try:
            response = self.client.chat_getPermalink(
                channel=channel,
                message_ts=thread_ts
            )
            return response.data
        except SlackApiError as e:
            return None


class SlackCallbacks:

    def __init__( self ):
        self.action_cache = {}
        self.command_cache = {}

    def register_action( self, key, function ):
        if key in self.action_cache:
            raise ImportError(f'{key} used in multiple dispatching for slack.')
        if not callable(function):
            raise ValueError('function is not callable')

        self.action_cache[key] = function

    def register_command( self, key, function ):
        if key in self.action_cache:
            raise ImportError(f'{key} used in multiple dispatching for slack.')
        if not callable(function):
            raise ValueError('function is not callable')
        self.command_cache[key] = function

    def dispatch( self, payload ):
        # if command or action lookup key
        if 'command' in payload:
            command_key = payload['command']
            if 'dev-' in command_key:
                command_key = command_key.replace('dev-','')
            return self.command_cache[command_key]( payload )
        elif payload['type'] == 'block_actions' and 'actions' in payload:
            for action in payload['actions']:
                key = action['action_id']
                self.action_cache[key]( payload )
            return True

# =============

# singleton
slack_dispatch = SlackCallbacks()
