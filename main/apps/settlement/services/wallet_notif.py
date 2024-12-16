from django.conf import settings
from main.apps.core.utils.slack import SlackNotification
from main.apps.oems.backend.slack_utils import make_buttons, make_header, make_input_section

from main.apps.settlement.models.wallet import Wallet

SLACK_CLIENT = None

class WalletActionService:
    wallet:Wallet

    def __init__(self, wallet:Wallet) -> None:
        self.wallet = wallet

    def get_notification_client(self) -> SlackNotification:
        global SLACK_CLIENT
        if SLACK_CLIENT is None:
            SLACK_CLIENT = SlackNotification()
        return SLACK_CLIENT

    def send_deletion_notification(self):
        if settings.SLACK_NOTIFICATIONS_CHANNEL:
            channel = settings.SLACK_NOTIFICATIONS_CHANNEL

            text = f'Request deletion for wallet id {self.wallet.wallet_id}'

            blocks = []
            blocks.append(make_header(text))
            blocks.append(make_input_section('wallet_id', 'Enter Wallet ID to Confirm'))
            blocks.append(make_buttons({'wallet_rem_req': 'confirm'}))

            sn = self.get_notification_client()
            sn.send_blocks(channel=channel, text=str(self.wallet.wallet_id),
                           blocks=blocks, return_data=True)
