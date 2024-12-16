import itertools
from typing import List

import pytz
import holidays

# some caching stuff
from cachetools import cached, LRUCache, TTLCache

# import pandas as pd
from rest_framework import status
from rest_framework import serializers
from datetime import date, timedelta, datetime, time
from dateutil.relativedelta import relativedelta

from django.db import connection

from main.apps.oems.api.utils.response import ErrorResponse, Response
from main.apps.oems.backend.trading_utils import get_reference_data
from main.apps.oems.backend.datetime_index import DatetimeIndex

# TODO: make a union type for datetime | date as well as an optional type

# ==========

def get_hol_codes( mkt, usd_default=True ):

	ref  = get_reference_data( mkt )
	if not ref:
		if usd_default:
			return ['NYB'], 2 # assume T+2
		return ErrorResponse('Market unsupported', status=status.HTTP_400_BAD_REQUEST)

	hol_codes = ref['SYMBOLOGY']['FINCAL']['HOL_CAL_CODES']
	if not hol_codes:
		if usd_default:
			return ['NYB'], 2 # assume T+2
		return ErrorResponse('Market unsupported', status=status.HTTP_400_BAD_REQUEST)

	return hol_codes, ref['SETTLEMENT_DAYS']

def get_trading_calendar_codes( mkt, use_exec=True ):

	ref  = get_reference_data( mkt )
	if not ref:
		return ErrorResponse('Market unsupported', status=status.HTTP_400_BAD_REQUEST)

	fc = ref['SYMBOLOGY']['FINCAL']
	cen_code = fc['EXEC_CEN_CODE'] or fc['CEN_CODE'] if use_exec else fc['CEN_CODE']

	if not cen_code:
		return ErrorResponse('Market unsupported', status=status.HTTP_400_BAD_REQUEST)

	return cen_code

# =====

HOLIDAY_TABLE = 'marketdata_tradingholidaysfincal'
TRADING_CALENDAR_TABLE = 'marketdata_tradingcalendarfincal'

# =====

def get_non_settlement_days( mkt, start_date, end_date, date_only=True, table_name=HOLIDAY_TABLE ):

	hol_codes, sdays = get_hol_codes( mkt )

	shc = ','.join(map(lambda x: f"'{x}'", hol_codes))
	# TODO: really union weekends + these
	sql = f'select distinct(date) from {table_name} where code in ({shc}) and date >= \'{start_date.isoformat()}\' and date <= \'{end_date.isoformat()}\''

	ret = []

	with connection.cursor() as cursor:
		cursor.execute(sql)
		ret = cursor.fetchall()

	return list(itertools.chain.from_iterable(ret))

def get_settlement_days( mkt, start_date, end_date, reverse=False, limit=None, as_index=False, table_name=HOLIDAY_TABLE ):

	hol_codes, sdays = get_hol_codes( mkt )

	# TODO: if middle east weekends, change this code
	shc = ','.join(map(lambda x: f"'{x}'", hol_codes))
	srt = 'desc' if reverse else 'asc'
	ending = f' limit {limit};' if limit else ';'

	# TODO: in TriCol, you don't actually need to pull out weekend + NULL
	sql = f"WITH date_series as (SELECT date FROM generate_series('{start_date.isoformat()}'::date, '{end_date.isoformat()}'::date, '1 day') AS s(date) WHERE EXTRACT(ISODOW FROM date) < 6) select ds.date from date_series ds left join ( select date from {table_name} where code in ({shc}) ) nsd on ds.date = nsd.date where nsd.date is null order by ds.date {srt}{ending}"

	with connection.cursor() as cursor:
		cursor.execute(sql)
		ret = cursor.fetchall()

	if as_index:
		return DatetimeIndex( _.date() for _ in itertools.chain.from_iterable(ret) )

	return list(itertools.chain.from_iterable(ret))


def is_valid_settlement_day( mkt, day, table_name=HOLIDAY_TABLE ):

	hol_codes, sdays = get_hol_codes( mkt )

	# TODO: if middle east weekend don't do this
	if day.weekday() > 4:
		return False

	shc = ','.join(map(lambda x: f"'{x}'", hol_codes))
	sql = f"SELECT EXISTS (SELECT 1 FROM {table_name} WHERE code in ({shc}) and date = '{day.isoformat()}') as date_exists;"

	with connection.cursor() as cursor:
		cursor.execute(sql)
		row = cursor.fetchone()

	return (not row[0])


def next_valid_settlement_day( mkt, day, table_name=HOLIDAY_TABLE ):
	start_date = day + timedelta(days=1)
	end_date = day + timedelta(days=14)
	days = get_settlement_days( mkt, start_date, end_date, limit=1 )
	try:
		return days[0].date() # first settlement
	except:
		raise
		return None

def prev_valid_settlement_day( mkt, day, table_name=HOLIDAY_TABLE ):
	start_date = day - timedelta(days=14)
	end_date = day
	days = get_settlement_days( mkt, start_date, end_date, reverse=True, limit=1 )
	try:
		return days[0].date() # first settlement
	except:
		return None

# ====================================================================

def get_current_mkt_session( mkt, dt, flds=['trade_date','activity','gmtt_open','gmtt_close'], order_by=['trade_date','gmtt_open','gmtt_close'], limit=None, table_name=TRADING_CALENDAR_TABLE ):

	cen_code = get_trading_calendar_codes( mkt )

	ending = f' limit {limit};' if limit else ';'
	ds  = dt.isoformat()
	sql = f"""select {','.join(flds)} from {table_name} where cen_code = '{cen_code}' and activity is not null and functions like '%4M%' and '{ds}' >= gmtt_open and '{ds}' < gmtt_close order by {','.join(order_by)}{ending}"""

	with connection.cursor() as cursor:
		cursor.execute(sql)
		ret = cursor.fetchall()

	return [dict(zip(flds,row)) for row in ret]

def get_next_mkt_session( mkt, dt, flds=['trade_date','activity','gmtt_open','gmtt_close'], order_by=['trade_date','gmtt_open','gmtt_close'], limit=1, table_name=TRADING_CALENDAR_TABLE ):

	cen_code = get_trading_calendar_codes( mkt )

	ending = f' limit {limit};' if limit else ';'
	ds  = dt.isoformat()
	sql = f"""select {','.join(flds)} from {table_name} where cen_code = '{cen_code}' and activity is not null and functions like '%4M%' and '{ds}' < gmtt_open order by {','.join(order_by)}{ending}"""

	with connection.cursor() as cursor:
		cursor.execute(sql)
		ret = cursor.fetchall()

	return [dict(zip(flds,row)) for row in ret]

def get_current_or_next_mkt_session( mkt, dt, **kwargs ):
	session = get_current_mkt_session( mkt, dt, **kwargs )
	is_open = bool(session)
	if not is_open:
		session = get_next_mkt_session( mkt, dt, **kwargs )
	return is_open, session[0] if session else None

# ====================================================================
# TODO: make this a class or config or something

TENOR_MAP = {
	'ON': -2, # Overnight
	'TN': -1, # tomorrow next
	'SPOT': 0, # Spot
	'SN': 1, # Spot Next
	'SW': 7, # Spot Week
	'1D': 1,
	'2D': 2,
	'3D': 3,
	'1W': 7,
	'2W': 14,
	'3W': 21,
	'1M': 31,
	'2M': 62,
	'3M': 93,
	'4M': 124,
	'5M': 155,
	'6M': 186,
	'7M': 217,
	'8M': 248,
	'9M': 279,
	'1Y': 366,
	# 15M, 18M, 21M, 2Y - we do not have calendars to support these
	# These are special dates
	'BMF1': 31,
	'BMF2': 62,
	'IMM1': 93,
	'IMM2': 186,
	'IMM3': 280,
	'IMM4': 370,
	'EOM1': 32,
	'EOM2': 64,
	'EOM3': 96,
	'EOM4': 124,
	'EOM5': 155,
	'EOM6': 186,
}

# =======================

def get_ref_date( mkt: str, dt=None ):

	ref = get_reference_data( mkt )

	# TODO: weekends??

	if mkt == 'NZDUSD' or mkt == 'USDNZD':
		if dt is None:
			localtz = pytz.timezone('Pacific/Auckland')
			dt  = datetime.now(localtz)
		# NOTE: exception for NZDUSD, value-dates change at 7AM Auckland

		if dt.weekday() <= 4 and dt.hour < 7:
			ret = dt.date()
		else:
			ret = dt.date() + timedelta(days=1)
		# TODO: do NDFs need their dates converted or use New York if ref['INSTR_TYPE'] == 'NDF':
	else:
		if dt is None:
			localtz = pytz.timezone('America/New_York')
			dt = datetime.now(localtz)
		# NOTE: value-dates change at 5PM New York Mon-Thursday
		if dt.weekday() <= 4 and dt.hour < 17:
			ret = dt.date()
		else:
			ret = dt.date() + timedelta(days=1)

	return ret

# =======================

def contains(tgt: str, substrings: List[str]) -> bool:
    return any(sub in tgt for sub in substrings)

def is_us_bank_holiday( dt: date ) -> bool:
	if not hasattr(is_us_bank_holiday, 'calendar'):
		is_us_bank_holiday.calendar = holidays.US()
	return (dt in is_us_bank_holiday.calendar)

def next_weekday(given_date: date) -> date:
    weekday = given_date.weekday()
    # If it's Friday, add 3 days, if it's Saturday, add 2 days,
    # otherwise, add 1 day (for Sunday to Thursday)
    days_to_add = 3 if weekday == 4 else (2 if weekday == 5 else 1)
    return given_date + timedelta(days=days_to_add)

def is_t1_us_bank_holiday( ref_dt: date ) -> bool:
	next_dt = next_weekday(ref_dt)
	return is_us_bank_holiday( next_dt )

def parse_tenor( tenor, padding=0 ):

	if tenor in TENOR_MAP:
		return TENOR_MAP[tenor]

	n    = int(tenor[:-1])
	freq = tenor[-1]
	if freq == 'D':
		days = n
	elif freq == 'W':
		days = 7 * n
	elif freq == 'M':
		days = 30 * n
		# TODO: there is a special rule for end-end trading where the spot
		# date falls on the end of a given month
	elif freq == 'Y':
		days = 365 * n
	else:
		raise ValueError

	return days + padding

def get_trade_date_from_value_date( mkt, value_date, settlement_days=None ):

	ref = get_reference_data( mkt )
	spot_days = ref['SETTLEMENT_DAYS'] if ref else 2
	sdt = value_date - timedelta(days=20)
	edt = value_date + timedelta(days=3)

	valid_days = get_settlement_days( mkt, start_date=sdt, end_date=edt, as_index=True ) if settlement_days is None else settlement_days

	ind = valid_days.index_le(value_date)
	prev_vd = valid_days[ind-spot_days]

	return prev_vd

def get_spot_dt( mkt, ref_dt=None, sdt=None, edt=None, tenor='1M', pad=10, settlement_days=None ):

	if not ref_dt:
		ref_dt = get_ref_date( mkt )
	elif isinstance(ref_dt, datetime):
		ref_dt = get_ref_date( mkt, dt=ref_dt )

	ref = get_reference_data( mkt )
	spot = ref['SETTLEMENT_DAYS'] if ref else 2

	if contains(mkt, ['ARS','CLP','MXN']) and is_t1_us_bank_holiday( ref_dt ):
		spot = 3 # if T+1 is US holiday, move spot to 3

	if sdt is None:
		sdt = ref_dt - timedelta(days=pad)

	if edt is None:
		day_count  = parse_tenor(tenor, padding=7)
		edt        = ref_dt + timedelta(days=day_count)

	sdt -= timedelta(days=pad)
	edt += timedelta(days=pad)

	valid_days = get_settlement_days( mkt, start_date=sdt, end_date=edt, as_index=True ) if settlement_days is None else settlement_days

	if not valid_days:
		raise ValueError

	# =========================================================================

	ref     = valid_days.index_le( ref_dt ) # NOTE: unclear if this should be LE/GE
	spot_dt = valid_days[ref+spot]

	return spot_dt, valid_days, spot

# =======================

def get_fx_spot_info( mkt: str, dt=None, ref_dt=None, pad: int=10, settlement_days=None ):

	if ref_dt is None:
		ref_dt = get_ref_date( mkt, dt=dt )

	# =========================================================================

	spot_dt, valid_days, spot = get_spot_dt( mkt, ref_dt, pad=pad, settlement_days=settlement_days )

	return { 'spot_value_date': spot_dt, 'settlement_days': spot, 'days': (spot_dt-ref_dt).days }

# ========================

def get_fx_fixing_dt( mkt: str, value_date, settlement_days=None, pad=10 ):

	ref = get_reference_data( mkt )
	sdays = ref['SETTLEMENT_DAYS'] if ref else 2

	if settlement_days:
		valid_days = settlement_days
	else:
		sdt        = value_date - timedelta(days=pad)
		edt        = value_date + timedelta(days=pad)
		valid_days = get_settlement_days( mkt, start_date=sdt, end_date=edt, as_index=True )

	if not valid_days:
		raise ValueError

	# =========================================================================

	check     = valid_days.index_le( value_date ) # NOTE: unclear if this should be LE/GE
	fixing_dt = valid_days[check-sdays]

	return fixing_dt

def get_fx_settlement_info( mkt: str, dt=None, ref_dt=None, tenor='SPOT', include_fix_date=False, pad: int=10, settlement_days=None ) -> dict:

	if ref_dt is None:
		ref_dt = get_ref_date( mkt, dt=dt )

	# =========================================================================

	spot_dt, valid_days, spot = get_spot_dt( mkt, ref_dt, tenor=tenor, pad=pad, settlement_days=settlement_days )

	fixing_dt = None
	settle_dt = None

	if tenor == 'SPOT' or tenor == 'SP':
		check_dt = spot_dt
	elif tenor == 'SN':
		check_dt = spot_dt + timedelta(days=1)
	elif tenor == 'ON':
		check_dt = ref_dt
	elif tenor == 'TN':
		check_dt = ref_dt + timedelta(days=1)
	elif tenor == 'SW':
		# spot week is spot + 7
		check_dt = spot_dt + timedelta(days=7)
	elif tenor.startswith('IMM'):
		raise NotImplementedError
		n        = int(tenor[3:])
		ind      = imm_dates.index_ge( spot_dt )
		check_dt = imm_dates[ind+(n-1)] # 3rd Wednesday
	elif tenor.startswith('BMF'):
		raise NotImplementedError
		n         = int(tenor[3:])
		ind       = uc_dates.index_ge( spot_dt )
		check_dt  = uc_dates[ind+(n-1)] # 1st monday
		fixing_dt = uc_dates[ind+(n-1)][1]
	elif tenor.startswith('EOM'):
		n = int(tenor[3:])
		if n > 1:
			last_day_of_month = ref_dt + relativedelta(months=(n-1)) + relativedelta(day=31)
		else:
			last_day_of_month = ref_dt + relativedelta(day=31)
		check = valid_days.index_le( last_day_of_month )
		settle_dt = valid_days[check]
	else:
		n    = int(tenor[:-1])
		freq = tenor[-1]

		if freq == 'D':
			check_dt = spot_dt + timedelta(days=n)
		elif freq == 'W':
			check_dt = spot_dt + timedelta(days=(7*n))
		elif freq == 'M':
			# TODO: there is a special rule for end-end trading where the spot
			# date falls on the end of a given month
			if n > 12:
				print("WARN: we do not have reliable holiday calendars greater than 1Y forward", tenor)
			check_dt = spot_dt + relativedelta(months=n)
			check     = valid_days.index_ge( check_dt )
			settle_dt = valid_days[check]
			alt_settle_dt = valid_days[check-1]
			if settle_dt.month > alt_settle_dt.month:
				settle_dt = alt_settle_dt
		elif freq == 'Y':
			if n > 1:
				print("WARN: we do not have reliable holiday calendars greater than 1Y forward", tenor)
			check_dt = spot_dt + relativedelta(years=n)
			check     = valid_days.index_ge( check_dt )
			settle_dt = valid_days[check]
			alt_settle_dt = valid_days[check-1]
			if settle_dt.year > alt_settle_dt.year:
				settle_dt = alt_settle_dt
		else:
			raise ValueError

	if settle_dt is None:
		check     = valid_days.index_ge( check_dt )
		settle_dt = valid_days[check]

	days = (settle_dt-spot_dt).days
	alt_days = (settle_dt-ref_dt).days

	if include_fix_date and fixing_dt is None:
		# TODO: figure out if this is find the closest day to T-2 or 2 valid settlement days back
		fixing_dt = valid_days[check-spot]

	if include_fix_date:
		return { 'ref_date': ref_dt, 'tenor': tenor, 'spot_date': spot_dt, 'fixing_date': fixing_dt, 'settle_date': settle_dt, 'days': days, 'alt_days': alt_days }
	else:
		return { 'ref_date': ref_dt, 'tenor': tenor, 'spot_date': spot_dt, 'settle_date': settle_dt, 'days': days, 'alt_days': alt_days }

# =============================================================================

def get_valid_settlement_days_until( mkt: str, start_date=None, end_date=None, max_tenor='3M', as_index: bool=False, **kwargs ) -> list:

	start_date = start_date or date.today()

	if not end_date:
		info = get_fx_settlement_info( mkt, tenor=max_tenor, **kwargs )
		end_date = info['settle_date']

	return get_settlement_days( mkt, start_date, end_date, as_index=as_index )

# =============================================================================

def infer_valid_settlement_day( mkt, day, rule='modified_follow'):

	if is_valid_settlement_day( mkt, day ):
		return day
	elif rule == 'reject':
		return None
	elif rule == 'modified_follow':
		candidate = next_valid_settlement_day( mkt, day )
		if candidate.year > day.year or candidate.month > day.month:
			return prev_valid_settlement_day( mkt, day )
		return candidate
	elif rule == 'next':
		return next_valid_settlement_day( mkt, day )
	elif rule == 'previous':
		return prev_valid_settlement_day( mkt, day )
	else:
		return None

# =============================================================================


def infer_tenor( mkt, value_date ):
	pass

# =============================================================================

class SettlementCalendar:

	def __init__( self ):
		#self.cache = {} # LRUcache()
		pass

	def get_spot_date(self, pair, ref_date):
		ref_dt = get_ref_date( pair, dt=ref_date )
		spot_dt, settlement_days, spot_offset = get_spot_dt( pair, ref_dt, tenor='1M' )
		# self.cache[(fxpair.market, ref_date,)] = spot_dt
		return spot_dt

	def get_forward_days(self, pair, ref_date, tenor: str, fld='days') -> int:
		if tenor == 'ON':
			return -2
		elif tenor == 'TN':
			return -1
		else:
			info = get_fx_settlement_info( pair, dt=ref_date, tenor=tenor )
			return info[fld]

# =============================================================================

def get_value_date_cutoff( market_name, ref_date = None ):
	tz = pytz.timezone('America/New_York')
	if ref_date is None:
		now = datetime.now(tz)
	else:
		now = tz.localize(ref_date)
	tdy = now.date()
	if tdy.weekday() == 6:
		tdy += timedelta(days=1)
	# TODO: if nzd, use 7AM auckland
	value_date_cutoff = tz.localize(datetime.combine(tdy, time(17)))
	return value_date_cutoff

def infer_value_date( market_name, value_date ):

	value_date_cutoff = get_value_date_cutoff( market_name )
	spot_days = 1 if market_name in ('USDCAD', 'USDPHP', 'USDRUB', 'USDTRY') else 2
	spot_date_cutoff = tdy + timedelta(days=spot_days + 1) if now > value_date_cutoff else tdy + timedelta(
		days=spot_days)

	if isinstance(value_date, str):
		if value_date == 'SPOT':
			value_date = tdy + timedelta(days=spot_days)
		elif value_date == 'RTP':
			value_date = tdy
		elif value_date == 'EOD':
			value_date = tdy
		elif value_date == 'TOM':
			value_date = tdy + timedelta(days=1)
		elif value_date == 'EOM':
			# if its a forward figure out the fixing date
			info = get_fx_settlement_info(market_name, dt=datetime.utcnow(), tenor='EOM1',
										  include_fix_date=True)
			# if you are a settlement date
			value_date = info['settle_date']
		else:
			raise serializers.ValidationError(f"value_date can only be SPOT, RTP, EOD, TOM, EOM or a date.")
	elif value_date < tdy:
		raise serializers.ValidationError(
			f"value_date must be >= today ({value_date.isoformat()} < {tdy.isoformat()})")
	elif value_date <= spot_date_cutoff:
		value_date = value_date_cutoff.date()  # to be safe
	else:
		# NOTE: check that forward value date is valid. if it isn't, use the convention to fix it or error.
		valid_value_date = infer_valid_settlement_day(market_name, value_date,
													  rule='modf')

		if not valid_value_date or valid_value_date < tdy:
			raise serializers.ValidationError(f"Invalid value_date provided ({value_date.isoformat()})")

		value_date = valid_value_date

	return value_date

# =============================================================================


if __name__ == "__main__":

	mkt = 'USDINR'

	if True:
		info = get_fx_spot_info( mkt )
		print( info )

	if False:
		start_date = date.today()
		end_date = start_date + timedelta(days=30)
		sd = get_settlement_days( mkt, start_date, end_date, as_index=True )

	if False:
		cal = SettlementCalendar()
		sp  = cal.get_spot_date( 'EURUSD', datetime.today() )

	if False:
		tmp = get_fx_settlement_info( 'USDKES', tenor='1M' )

	if False:
		# ref_dt = get_ref_date( mkt )
		tmp = get_fx_settlement_info( mkt, tenor='5Y', include_fix_date=False )

	if False:
		dt = infer_valid_settlement_day( mkt, datetime.today()+timedelta(9), rule='MODF')
		print( dt )

	if False:
		start_date = date.today()
		end_date = start_date + timedelta(days=30)

		if True:
			cur_session = get_current_mkt_session( mkt, datetime.now() )
			nxt_session = get_next_mkt_session( mkt, datetime.now() )

			print('current trading session:', cur_session)
			print('next trading session:', nxt_session)

		if True:
			nsd = get_non_settlement_days( mkt, start_date, end_date )
			for x in nsd:
				print('nsd:', x)
			sd = get_settlement_days( mkt, start_date, end_date, as_index=True )
			for x in sd:
				print('settlement:', x)

		if True:

			dt = datetime(2024, 3, 29)

			valid = is_valid_settlement_day( mkt, dt )
			nxt = next_valid_settlement_day( mkt, dt )
			prev = prev_valid_settlement_day( mkt, dt )

			print('dt', dt, 'is_valid_settle', valid, 'next settle', nxt, 'prev settle', prev)
