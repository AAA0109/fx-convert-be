from enum import Enum


class WebhookEventType(Enum):
    # Ticket events
    TICKET_CREATED = 'ticket.created'
    TICKET_UPDATED = 'ticket.updated'
    TICKET_CANCELED = 'ticket.canceled'

    # Trade events
    TRADE_CONFIRM = 'trade.confirm'
    TRADE_MTM = 'trade.mtm'
    TRADE_FIXING = 'trade.fixing'
    TRADE_SETTLEMENT = 'trade.settlement'

    # Margin events
    MARGIN_NOTICE = 'margin.notice'

    # Beneficiary events
    BENEFICIARY_CREATED = 'beneficiary.created'
    BENEFICIARY_UPDATED = 'beneficiary.updated'
    BENEFICIARY_CANCELED = 'beneficiary.canceled'


WEBHOOK_EVENTS = [
    {'name': 'Ticket Created', 'type': WebhookEventType.TICKET_CREATED.value},
    {'name': 'Ticket Updated', 'type': WebhookEventType.TICKET_UPDATED.value},
    {'name': 'Ticket Canceled', 'type': WebhookEventType.TICKET_CANCELED.value},
    {'name': 'Trade Confirm', 'type': WebhookEventType.TRADE_CONFIRM.value},
    {'name': 'Trade MTM', 'type': WebhookEventType.TRADE_MTM.value},
    {'name': 'Trade Fixing', 'type': WebhookEventType.TRADE_FIXING.value},
    {'name': 'Trade Settlement', 'type': WebhookEventType.TRADE_SETTLEMENT.value},
    {'name': 'Margin Notice', 'type': WebhookEventType.MARGIN_NOTICE.value},
    {'name': 'Beneficiary Created', 'type': WebhookEventType.BENEFICIARY_CREATED.value},
    {'name': 'Beneficiary Updated', 'type': WebhookEventType.BENEFICIARY_UPDATED.value},
    {'name': 'Beneficiary Deleted', 'type': WebhookEventType.BENEFICIARY_CANCELED.value},
]

WEBHOOK_EVENT_GROUPS = [
    {
        'name': 'All',
        'slug': 'all',
        'events': [event['type'] for event in WEBHOOK_EVENTS]
    },
    {
        'name': 'Trade',
        'slug': 'trade',
        'events': [
            WebhookEventType.TICKET_CREATED.value,
            WebhookEventType.TICKET_UPDATED.value,
            WebhookEventType.TICKET_CANCELED.value,
        ]
    },
    {
        'name': 'Drop Copy',
        'slug': 'drop_copy',
        'events': [
            WebhookEventType.TRADE_CONFIRM.value,
            WebhookEventType.TRADE_MTM.value,
            WebhookEventType.TRADE_FIXING.value,
            WebhookEventType.TRADE_SETTLEMENT.value,
        ]
    },
    {
        'name': 'Urgent',
        'slug': 'urgent',
        'events': [
            WebhookEventType.MARGIN_NOTICE.value,
        ]
    },
    {
        'name': 'Beneficiary',
        'slug': 'beneficiary',
        'events': [
            WebhookEventType.BENEFICIARY_CREATED.value,
            WebhookEventType.BENEFICIARY_UPDATED.value,
            WebhookEventType.BENEFICIARY_CANCELED.value,
        ]
    }
]
