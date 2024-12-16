
class TenorConverter(object):
    """
    Provides spot delay convention for all currencies, in addition to tenor conversion.

    Note, this class is not intended to perform lookups in db,
    which will be costly. The convention is fixed per pair, it is static. Note: we could provide from database
    and cache in the future
    """
    # TODO: fill this in
    delays = {"EUR/USD": 2}

    _tenor_mult = {"M": 30, "W": 7, "Y": 365, "D": 1}

    def delay_days(self, fx_pair_name: str) -> int:
        """
        Get the spot delay convention in days for the fx pair, by default return 2 if pair not found
        :param fx_pair_name: str, name of pair ("GBP/USD")
        :return: int, spot/settlement delay in days
        """
        return self.delays.get(fx_pair_name, 2)

    def get_days_from_tenor(self, tenor: str, fx_pair_name: str) -> int:
        """ Converts the tenor into days

        ON - Overnight, from today to tomorrow, spot lag of 0 and tenor of 1 day
        TN - Tomorrow-Next, from tomorrow to the next day, spot lag of 1 and tenor of 1 day
        SN - Spot-Next, from spot to the next day, market conventional spot lag and tenor of 1 day
        SW - Spot-Week, from spot for one week, market conventional spot lag and tenor of 1 week
        "Normal" tenors - 2W, 1M, 1Y etc - from spot for the specified period, market conventional spot lag
        Note: Spot lag (days) is usually 2 days, but differs by pair
        """

        duration = tenor[:-1]
        period = tenor[-1]

        if period == "N":
            if duration == "O":
                # ON - Overnight, from today to tomorrow, spot lag of 0 and tenor of 1 day
                return 1
            if duration == "T":
                # TN - Tomorrow-Next, from tomorrow to the next day, spot lag of 1 and tenor of 1 day
                return 2
            if duration == "S":
                # SN - Spot-Next, from spot to the next day, market conventional spot lag and tenor of 1 day
                # Note: Spot lag (days) is usually 2 days, but differs by pair
                return self.delay_days(fx_pair_name=fx_pair_name) + 1
            return 1 if duration == "O" else 2
        elif period == "W" and duration == "S":
            # SW - Spot-Week, from spot for one week, market conventional spot lag and tenor of 1 week
            return self.delay_days(fx_pair_name=fx_pair_name) + 7

        return int(duration) * self._tenor_mult[period]
