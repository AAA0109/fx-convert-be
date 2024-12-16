import operator

from collections.abc import MutableSequence
from datetime import datetime
from sortedcontainers import SortedList, SortedKeyList

# ================

class _Order:

	def __init__(self, direction, price, size, dt, obj=None, order_id=None):

		# in theory, python datetimes work as well
		if not isinstance(dt, datetime):
			raise TypeError("Date must be of type datetime")

		# in theory, float priorities also work
		if isinstance(price, int):
			price = float(price)
		if not isinstance(price, float):
			raise TypeError("Price must be float")

		self.direction = direction
		self.price = price
		self.size = size
		self.datetime = dt
		self.order_id = order_id  # order_id
		self.obj = obj

		self.__mult__ = 1 if self.direction == 0 else -1

	def __repr__(self):
		return f"Order(price={self.price}, size={self.size}, datetime={self.datetime.isoformat()}, order_id={self.order_id})"

	def __eq__(self, other):
		if other.__class__ is self.__class__:
			return (self.price, self.datetime) == (other.price, other.datetime)
		else:
			return NotImplemented

	def __ne__(self, other):
		result = self.__eq__(other)
		if result is NotImplemented:
			return NotImplemented
		else:
			return not result

	def __lt__(self, other):
		if (
			other.__class__ is self.__class__
			and other.direction == self.direction
			and other.__mult__ == self.__mult__
		):
			return (self.__mult__ * self.price, self.datetime) < (
				self.__mult__ * other.price,
				other.datetime,
			)
		else:
			return NotImplemented

	def __le__(self, other):
		if (
			other.__class__ is self.__class__
			and other.direction == self.direction
			and other.__mult__ == self.__mult__
		):
			return (self.__mult__ * self.price, self.datetime) <= (
				self.__mult__ * other.price,
				other.datetime,
			)
		else:
			return NotImplemented

	def __gt__(self, other):
		if (
			other.__class__ is self.__class__
			and other.direction == self.direction
			and other.__mult__ == self.__mult__
		):
			return (self.__mult__ * self.price, self.datetime) > (
				self.__mult__ * other.price,
				other.datetime,
			)
		else:
			return NotImplemented

	def __ge__(self, other):
		if (
			other.__class__ is self.__class__
			and other.direction == self.direction
			and other.__mult__ == self.__mult__
		):
			return (self.__mult__ * self.price, self.datetime) >= (
				self.__mult__ * other.price,
				other.datetime,
			)
		else:
			return NotImplemented

	def __hash__(self):
		return hash(self.order_id or self)

# ==========

class BookSide(SortedList):

	"""
	This is not a great data structure for a real limit order book.
	Just a placeholder because i'm lazy.

	# direction is a boolean (0/1, False/True, etc.) where:
	# 0/False is ascending - lowest first - ask side
	# 1/True is descending - highest first - bid side
	"""
	def __init__(self, direction=0, tag=None, iterable=None):
		super().__init__(self)
		self.direction = direction
		self.size = 0
		self.tag = tag

	# override SortedList new __reduce__ function that breaks pickle
	def __reduce__(self):
		return MutableSequence.__reduce__(self)

	def __new__(cls, direction=0, tag=None, iterable=None):
		"""
		SortedList implements new so must define this... stupid
		"""
		return object.__new__(cls)

	# we expect that order_ids are unique, otherwise you will get unexpected behavior
	# when accessing (the first match found is returned/deleted/replaced)
	def add(self, price, size, dt, obj=None, order_id=None):
		_order = _Order(self.direction, price, size, dt, obj=obj, order_id=order_id)
		SortedList.add(self, _order)
		self.size += 1

	def add_object(self, order):
		SortedList.add(self, order)
		self.size += 1

	def clear(self):
		SortedList.clear(self)
		self.size = 0

	def peek(self):
		if self.size > 0:
			return self.__getitem__(0)
		else:
			return None

	def next(self):
		if self.size > 0:
			return self.pop(0)
		else:
			return None

	def get_order_id(self, order_id):
		if self.size > 0 and order_id:
			for order in self:
				if order.order_id == order_id:
					return order
		else:
			return None

	def remove_order_id(self, order_id):
		if self.size > 0 and order_id:
			d = None
			for i, order in enumerate(self):
				if order.order_id == order_id:
					d = i
					break
			if d is not None:
				self.__delitem__(d)
				self.size -= 1
				return True
		return False

	def replace_order_id(self, order_id, price, size, dt, obj=None):
		if order_id:
			self.remove_order_id(order_id)
			self.add(price, size, dt, order_id=order_id, obj=obj)
			return True
		return False

	def top_of_book(self):
		# this only does price for now
		o = self.peek()
		return o.price if o else None

	def adjust_order_size( self, order_id, new_size ):
		if self.size > 0 and order_id:
			o = None
			for order in self:
				if order.order_id==order_id:
					o = order
					break
			if o is not None:
				o.size = new_size
				return True
		return False

	def get_volume_at(self, price, aggregate=True):
		volume = 0
		if self.size > 0:
			if aggregate:
				op = operator.ge if self.direction == 1 else operator.le
			else:
				op = operator.eq
			for order in self:
				if op(order.price, price):
					volume += order.size
				else:
					break
		return volume

	# =============================
	# these should be implemented one level higher in the OrderBook
	# def get_bbo_volume( self ):
	# Get total size of best bid/offer

	# def get_volume_at( self, price ):
	# Get total size at given price

# ==========

class OrderBook:

	def __init__( self ):
		self.bids = BookSide(direction=1)
		self.asks = BookSide(direction=0)

	def store_bid( self, key, price, size, dt):
		self.bids.replace_order_id(key, price, size, dt)

	def store_ask( self, key, price, size, dt):
		self.asks.replace_order_id(key, price, size, dt)

	def bbo( self ):
		best_bid = self.bids.top_of_book()
		best_ask = self.asks.top_of_book()
		return best_bid, best_ask

# ==========

if __name__ == "__main__":
	ob = OrderBook()
	ob.store_bid( 'test1', 100.0, 1, datetime.now() )
	ob.store_bid( 'test2', 99.0, 1, datetime.now() )
	ob.store_ask( 'test1', 101.0, 1, datetime.now() )
	ob.store_ask( 'test2', 102.0, 1, datetime.now() )
