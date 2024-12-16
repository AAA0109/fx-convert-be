
from main.apps.oems.models.ticket import Ticket
from main.apps.oems.backend.calendar_utils import infer_valid_settlement_day, get_spot_dt
from main.apps.oems.backend.ccy_utils import determine_rate_side

class CalendarService:

	def __init__( self ):
		...

	def infer_value_dates( self, buy_currency, sell_currency, dates, rule=Ticket.DateConvs.MODF ):
		fxpair, side = determine_rate_side(sell_currency, buy_currency)
		spot_dt, valid_days, spot_days  = get_spot_dt( fxpair.market )
		ret = set()
		for dt in dates:
			if dt <= spot_dt:
				valid_dt = spot_dt
			else:
				valid_dt = infer_valid_settlement_day( fxpair.market, dt, rule=rule )
			ret.add(valid_dt)
		return sorted(list(ret))
		

