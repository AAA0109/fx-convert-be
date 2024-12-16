"""
Margin Notice	margin.notice
Trade Settlement	trade.settlement
Trade Fixing	trade.fixing
Trade MTM	trade.mtm
Trade Confirm	trade.confirm
Ticket Canceled	ticket.canceled
Ticket Updated	ticket.updated
Ticket Created	ticket.created
"""


class WEBHOOK_EVENTS:
    DEPOSIT_NOTICE = 'deposit.notice'
    MARGIN_NOTICE = 'margin.notice'
    PORTFOLIO_MTM = 'portfolio.mtm'

    TRADE_SETTLE = 'trade.settlement'
    TRADE_FIXING = 'trade.fixing'
    TRADE_MTM = 'trade.mtm'
    TRADE_CONFIRM = 'trade.confirm'

    TICKET_CANCELED = 'ticket.canceled'
    TICKET_UPDATED = 'ticket.updated'
    TICKET_CREATED = 'ticket.created'

    BENEFICIARY_CREATED = 'beneficiary.created'
    BENEFICIARY_UPDATED = 'beneficiary.updated'
    BENEFICIARY_DELETED = 'beneficiary.canceled'

# ==========
# map of payload fields

"""
WEBHOOOK_FIELDS = {
    DEPOSIT_NOTICE: None,
    MARGIN_NOTICE: None,
    TRADE_SETTLE: None,
    TRADE_CONFIRM: None,
    TICKET_CANCELED: None,
    TICKET_CREATED: None,
    TICKET_UPDATED: None
}
"""

