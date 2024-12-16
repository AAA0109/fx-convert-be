

# ============================

class TimeSeriesApi:

	def __init__( self, table_name, fields, conditions=None, schema=None, date_field='date', order_by='date', direction='asc' ):

		self.table_name = table_name
		self.schema = schema
		self.date_field = date_field
		self.order_by = order_by
		self.direction = direction
		self.fields = fields
		self.conditions = conditions

	def expand_fields( self, fields ):
		ret = []
		for field in fields:
			ret.append( f'"{self.fields[field]}"' )
		return ','.join(ret)

	@staticmethod
	def reverse_direction( direction ):
		return 'asc' if direction == 'desc' else 'desc'

	def __call__( self, fields=None, start_date=None, end_date=None, conditions=None, limit=None, reverse=False ):

		sql = f'select {self.expand_fields(fields)} from "{self.table_name}"'

		where = []

		if start_date:
			where.append(f'"{self.date_field}" >= {start_date.isoformat()}')

		if end_date:
			where.append(f'"{self.date_field}" < {end_date.isoformat()}')

		if self.conditions:
			where += self.conditions

		if conditions:
			where += conditions

		if where:
			sql += f" WHERE {' '.join(where)}"

		sql += f' order by {self.order_by} {self.reverse_direction(self.direction) if reverse else self.direction}'

		if limit:
			sql += f' limit {limit}'
			
		return sql

# ========================

ICE_FIELDS = {
	'd': 'date',
	'b': 'rate_bid',
	'a': 'rate_ask',
	'm': 'rate',
	'B': 'fwd_points_bid',
	'A': 'fwd_points_ask',
	'M': 'fwd_points',
	'D': 'days',
	'F': 'depo_base',
	'Q': 'depo_quote',
}

ice_eod_fx_spot_api = TimeSeriesApi( 'marketdata_fxspot', ICE_FIELDS) # conditions = 'cut_type = 1'
ice_eod_fx_forward_api = TimeSeriesApi( 'marketdata_fxforward', ICE_FIELDS) # conditiosn = cut_type = 1


if __name__ == "__main__":
	pass