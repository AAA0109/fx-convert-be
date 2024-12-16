from main.apps.payment.services.calendar import DATE_TYPE
from main.apps.settlement.models import Beneficiary

DELIVERY_METHODS = Beneficiary.PaymentSettlementMethod.choices
DATE_TYPES = [
    (DATE_TYPE.EXPEDITED, 'Expedited'),
    (DATE_TYPE.SPOT, 'Spot'),
    (DATE_TYPE.MAX_DATE, 'Max Date'),
    (DATE_TYPE.FORWARD, 'Forward'),
    (DATE_TYPE.TRADE_DATE, 'Trade Date'),
]
