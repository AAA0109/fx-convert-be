from collections.abc import MutableSequence

from sortedcontainers import SortedList, SortedKeyList
from datetime import datetime, date
from typing import Optional
from functools import wraps
import pandas as pd

# =========================

def wrapped_key(f):
    @wraps(f)
    def wrapper( x ):
        if isinstance(x, DatetimeIndex.INDEX_TYPES):
            return x
        return f(x)
    return wrapper

def identity( x ):
    return x

# ==========================

class DatetimeIndex(SortedKeyList):

    """
    This is an amazing date-time cache that makes it very easy
    to cache data that can be indexed using a b-tree. You can easily
    lookup indexes
    """

    INDEX_TYPES = (int, datetime, date)

    def __init__( self, *args, index_fld=None, max_size=None, max_age=None, age=None, key=identity ):
        super().__init__(*args, key=wrapped_key(key) )
        # unfortunately there is some crazy init behavior
        # init calls __new__ first and doesn't pass generic kwargs
        # easy fix in the lib but sucks.
        self._index_fld = index_fld
        self._max_size = max_size
        self._max_age = max_age
        self._age = age # callable

    # =================================

    # override SortedList new __reduce__ function that breaks pickle
    def __reduce__(self):
        return MutableSequence.__reduce__(self)

    def __new__(cls, *args, **kwargs):
        """
        SortedList implements new so must define this... stupid
        """
        return object.__new__(cls)

    # =================================

    def set_index( self, index ):
        self._index_fld = index

    def set_max_size( self, max_size ):
        self._max_size = max_size
        # should we ensure cache here?
        self.ensure_cache()

    def set_max_age( self, max_age, age ):
        assert callable(age)
        self._max_age = max_age
        self._age = age
        # should we ensure cache here?
        self.ensure_cache()

    def _preadd_cache( self ):
        if not self: return
        # ensure max size is maintained
        if self._max_size:
            while len(self) >= self._max_size:
                # pop oldest entry
                del self[0]

        # ensure max age is maintained
        # self._age is a callable
        if self._max_age:
            while self:
                if self._age(self, self[0]) > self._max_age:
                    del self[0]
                else:
                    break

    def ensure_cache( self ):
        if not self: return
        # ensure max size is maintained
        if self._max_size:
            while len(self) > self._max_size:
                # pop oldest entry
                del self[0]

        # ensure max age is maintained
        # self._age is a callable
        if self._max_age:
            while self:
                if self._age(self, self[0]) > self._max_age:
                    del self[0]
                else:
                    break

    def add( self, value ):
        self._preadd_cache()
        return super().add(value)

    def append( self, value ):
        self._preadd_cache()
        return self.add( value )

    def insert( self, value ):
        self._preadd_cache()
        index = self.index_eq(value)
        if index is None:
            return self.add( value )
        else:
            raise ValueError('Duplicate index added')

    # =====================

    def index_eq(self, value: datetime) -> Optional[int]:
        """Return the datetime equal to the entered value."""
        if not self: return
        index = self.bisect_left(value)
        if 0 <= index < len(self):
            val = self[index]
            if not isinstance(val, self.INDEX_TYPES):
                val = self._key(val)
            if not isinstance(value, self.INDEX_TYPES):
                value = self._key(value)
            if val == value:
                return index

    def index_le(self, value: datetime) -> Optional[int]:
        """Return the datetime equal to or less than the entered value."""
        if not self: return
        index = self.bisect_left(value)
        if index >= 0:
            try:
                val = self[index]
            except IndexError:
                return len(self) - 1
            if not isinstance(val, self.INDEX_TYPES):
                val = self._key(val)
            if not isinstance(value, self.INDEX_TYPES):
                value = self._key(value)
            if val == value:
                return index
            return index - 1 if index != 0 else None
        return None

    def index_lt(self, value: datetime) -> Optional[int]:
        """Return the datetime less than the entered value."""
        if not self: return
        index = self.bisect_left(value)
        if index >= 0:
            try:
                val = self[index]
            except IndexError:
                return len(self) - 1
            if not isinstance(val, self.INDEX_TYPES):
                val = self._key(val)
            if not isinstance(value, self.INDEX_TYPES):
                value = self._key(value)
            if val >= value:
                return index - 1 if index != 0 else None
            return index
        return None

    def index_ge(self, value: datetime) -> Optional[int]:
        """Return the datetime greater than or equal to the entered value."""
        if not self: return
        index = self.bisect_left(value)
        if index < len(self):
            return index
        return None

    def index_gt(self, value: datetime) -> Optional[int]:
        """Return the datetime greater than the entered value."""
        if not self: return
        index = self.bisect_left(value)
        if index < len(self):
            val = self[index]
            if not isinstance(val, self.INDEX_TYPES):
                val = self._key(val)
            if not isinstance(value, self.INDEX_TYPES):
                value = self._key(value)
            if val == value:
                return index + 1 if index < len(self)-1 else None
            return index
        return None

    def index_of( self, value, comp = 'lt'):
        if not self: return
        index = None
        if comp == 'lt':
            index = self.index_lt( value )
        elif comp == 'le':
            index = self.index_le( value )
        elif comp == 'eq':
            index = self.index_eq( value )
        elif comp == 'gt':
            index = self.index_gt( value )
        elif comp == 'ge':
            index = self.index_ge( value )
        else:
            raise ValueError
        return index

    def find( self, value, comp='lt' ):
        index = self.index_of( value, comp=comp )
        if index is not None:
            return self[index]

    # ===================

    @staticmethod
    def convert_to_row( obj ):
        if isinstance(obj, (list, dict)):
            return obj
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return ({
                s: getattr(obj, s, None)
                for s in {
                    s
                    for cls in type(obj).__mro__
                    for s in getattr(cls, '__slots__', ())
                }
            })

    def to_df( self, start=None, end=None, istart=True, iend=True, **kwargs ):
        if self._index_fld and 'index' not in kwargs:
            kwargs['index'] = self._index_fld
        if start is None and end is None:
            data = [ self.convert_to_row(_) for _ in self ]
            return pd.DataFrame.from_records(data, **kwargs)
        if isinstance(start, int):
            it = sl.islice(start + 1 if istart else start, end + 1 if iend else end)
            data = [ self.convert_to_row(_) for _ in it ]
            return pd.DataFrame.from_records(data, **kwargs)
        else:
            it = sl.irange(start, end, inclusive=(istart,iend), **kwargs)
            data = [ self.convert_to_row(_) for _ in it ]
            return pd.DataFrame.from_records(data)

# ======================

if __name__ == "__main__":

    if False:
        from datetime import timedelta
        tdy = datetime.today().date()

        class Foo:
            def __init__(self, idx, value):
                self.index = idx
                self.value = value

        class Bar:
            __slot__ = ('index','value')
            def __init__(self, idx, value):
                self.index = idx
                self.value = value

        # ret = [ {'index': tdy + timedelta(i), 'close': 1.0 } for i in range( 5 ) ]
        ret = []
        for i in range(5):
            ret.append( Foo( tdy+timedelta(i), float(i)) )

        ret = []
        for i in range(5):
            ret.append( Bar( tdy+timedelta(i), float(i)))

        x = DatetimeIndex(ret, key=lambda x: x.index)
        x.set_index('index')
        df = x.to_df()

    # note that both cache conditions can be true

    if True:
        y = DatetimeIndex([1,2,3,4])
        y.set_max_size(3)

    if True:
        y = DatetimeIndex([1,2,3,4])

        # don't keep values smaller than max - val >= 5
        def age_calc( ls, val ):
            return max(ls) - val
        y.set_max_age(5, age_calc)

        for i in range(5, 10):
            y.add(i)
            print( i, y )
