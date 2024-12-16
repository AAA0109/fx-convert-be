import unittest

from django.conf import settings
from django.test import TestCase

from main.apps.core.utils.slack import SlackNotification


class SlackNotificationTestCase(TestCase):

    def setUp(self) -> None:
        # Create an instance of the SlackNotification class to use in the tests
        self.slack = SlackNotification()

    @unittest.skipIf(not settings.SLACK_RUN_TESTS, "Only run if SLACK_RUN_TESTS is set to True")
    def test_send_text_message_with_header(self):
        # Test sending a text message with a header
        thread_ts = self.slack.send_text_message(
            text="This is a test message with a header",
            is_header=True
        )
        # Ensure that the thread timestamp is returned and is a string
        self.assertTrue(isinstance(thread_ts, str))

    @unittest.skipIf(not settings.SLACK_RUN_TESTS, "Only run if SLACK_RUN_TESTS is set to True")
    def test_send_text_message_without_header(self):
        # Test sending a text message without a header
        thread_ts = self.slack.send_text_message(
            text="This is a test message without a header",
        )
        # Ensure that the thread timestamp is returned and is a string
        self.assertTrue(isinstance(thread_ts, str))

    @unittest.skipIf(not settings.SLACK_RUN_TESTS, "Only run if SLACK_RUN_TESTS is set to True")
    def test_send_text_message_in_thread(self):
        # Test sending a text message in a thread
        thread_ts = self.slack.send_text_message(
            text="This is a test message in a thread 123",
        )
        # Ensure that the thread timestamp is returned and is a string
        self.assertTrue(isinstance(thread_ts, str))

        # Test sending a reply to the thread
        reply_thread_ts = self.slack.send_text_message(
            text="This is a reply to the test message in the thread",
            thread_ts=thread_ts
        )
        # Ensure that the reply thread timestamp is returned and is a string
        self.assertTrue(isinstance(reply_thread_ts, str))

    @unittest.skipIf(not settings.SLACK_RUN_TESTS, "Only run if SLACK_RUN_TESTS is set to True")
    def test_send_mrkdwn_message(self):
        # Test sending a message with Markdown formatting
        thread_ts = self.slack.send_mrkdwn_message(
            mrkdwn="```This is a code block```",
            text="This is a test message with Markdown formatting",
        )
        # Ensure that the thread timestamp is returned and is a string
        self.assertTrue(isinstance(thread_ts, str))


if __name__ == '__main__':
    unittest.main()
