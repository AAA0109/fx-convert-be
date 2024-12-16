from enum import Enum


class LiquidityStatus(Enum):
    POOR = 'poor'
    GOOD = 'good'
    ACCEPTABLE = 'acceptable'

class MarketStatus(Enum):
    OPEN = 'open'
    CLOSE = 'close'
