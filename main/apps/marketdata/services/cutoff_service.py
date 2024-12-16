import pytz
import logging

from datetime import datetime, time
from typing import Optional

from main.apps.oems.backend.calendar_utils import get_next_mkt_session
from main.apps.oems.backend.exec_utils import get_best_execution_status


logger = logging.getLogger(__name__)


class CutoffProvider:
    session:str
    market:str
    NY_TZ:pytz.tzinfo.DstTzInfo = pytz.timezone('America/New_York')
    UTC_TZ:pytz.tzinfo.DstTzInfo = pytz.timezone('UTC')
    current_utc:datetime
    CUT_OFF:int = 16

    def __init__(self, market:str, session:str) -> None:
        self.session = session
        self.market = market
        self.current_utc = self.UTC_TZ.localize(datetime.utcnow())

    def __get_current_time(self, current_time:Optional[datetime] = None) -> datetime:
        if current_time is None:
            current_time = self.current_utc

        if current_time.tzinfo is None:
            current_time = self.UTC_TZ.localize(current_time)

        return current_time

    def __set_cutoff(self, current_time:datetime) -> Optional[datetime]:
        mod_cutoff = None
        next_market_session = get_next_mkt_session(mkt=self.market, dt=current_time)
        if next_market_session:
            mod_cutoff = self.NY_TZ.localize(datetime.combine(next_market_session[0]['trade_date'],
                                                              time(self.CUT_OFF))).astimezone(self.UTC_TZ)
        return mod_cutoff

    def __modify_cutoff_time_if_behind(self, cutoff_time:datetime,
                                     current_time:Optional[datetime] = None) -> datetime:
        """
        Modify cutoff if cutoff < current time
        """
        current_time = self.__get_current_time(current_time=current_time)

        if cutoff_time > current_time:
            return cutoff_time

        mod_cutoff = self.__set_cutoff(current_time=current_time)
        return mod_cutoff if mod_cutoff else cutoff_time

    def __modify_cutoff_if_weekend(self, cutoff_time:datetime,
                                 current_time:Optional[datetime] = None) -> datetime:
        """
        Modify cutoff on Weekend market
        """
        try:
            current_time = self.__get_current_time(current_time=current_time)
            mod_cutoff = self.__set_cutoff(current_time=current_time)
            return mod_cutoff if mod_cutoff else cutoff_time
        except Exception as e:
            logger.error(str(e), exc_info=True)
            pass
        return cutoff_time

    def modify_cutoff(self, cutoff_time:Optional[datetime] = None, current_time:Optional[datetime] = None) -> datetime:
        """
        Modify cutoff time on the Weekend or if it's behind current time
        """
        current_time = self.__get_current_time(current_time=current_time)
        if cutoff_time is None:
            cutoff_time = self.NY_TZ.localize(datetime.combine(current_time.date(),
                                                               time(self.CUT_OFF))).astimezone(self.UTC_TZ)

        if self.session != 'Weekend':
            return self.__modify_cutoff_time_if_behind(cutoff_time=cutoff_time, current_time=current_time)

        return self.__modify_cutoff_if_weekend(cutoff_time=cutoff_time, current_time=current_time)

    def modify_best_exec_status_for_weekend(self, cutoff_time:datetime, org_best_exec_status:dict) -> dict:
        if self.session == 'Weekend':
            return get_best_execution_status(market_name=self.market, ref_date=cutoff_time)
        return org_best_exec_status
