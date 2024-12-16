from typing import Dict

import numpy as np

from hdlib.Core.AccountInterface import AccountInterface

from hdlib.Core.FxPairInterface import FxPairInterface


def get_liquidity_adjusted_positions(account_exposures: Dict[FxPairInterface, Dict[AccountInterface, float]],
                                     desired_positions: Dict[FxPairInterface, Dict[AccountInterface, float]],
                                     liquidity_changes: Dict[FxPairInterface, float],
                                     ) -> Dict[FxPairInterface, Dict[AccountInterface, float]]:
    """
    A "liquidity absorption" happens when the system realizes that instead of acquiring a position to offset the FX
    risk of one account, instead other accounts with exposures in the opposite direction and that are not fully
    hedged can take on larger (more fully-hedged) positions, allowing the first account to take on a larger
    position (in the opposite direction, since their exposures are in opposite directions). The positions of the
    first account and the other accounts offset (internally), meaning we don't have to submit an order, or at least
    as large of an order to the OMS.

    To allow this to happen, we take the changes that the liquidity pool made, and use them to increase the magnitude
    of positions whose exposure is in the same direction as the change in position due to liquidity absorption.

    More of the benefit is given to accounts that have larger remaining exposures.

    Example:
                    Total Exposure  |  Fx Position  |   Remaining
        ---------------------------------------------------------------
        Account A:   +130,000       |   -100,000    |   +30,000
        Account B:    -50,000       |   10,000      |   -40,000
        Account C:    -70,000       |   20,000      |   -50,000
        ---------------------------------------------------------------
        Net Exposure: +10,000
        Net Requested Hedge: -70,000
        Liquidity: -60,000

        Liquidity absorption: -60,000

        Remaining exposure from Account A: None, since sign(Remaining exposure A) != sign(Liquidity absorption)
        Remaining exposure from Account B: -40,000
        Remaining exposure from Account B: -50,000
        Total: -90,000

        -60,000 / -90,000 = 0.666 or 2/3 ==> Fraction to adjust accounts.

        Adjustment to Account A: None, since sign(Remaining exposure A) != sign(Liquidity absorption)
        Adjustment to Account B: -(-40,000 * 2/3) = 26,666.666
        Adjustment to Account C: -(-50,000 * 2/3) = 33,333.333

        Final Fx Position for Account A: -100,000
        Final Fx Position for Account B: +36,666
        Final Fx Position for Account C: +53,333

    """

    changed_desired_positions = {}

    for fxpair, change in liquidity_changes.items():
        cash_exposures = account_exposures.get(fxpair, {})  # Should always find something.

        # Calculate remaining exposure.
        remaining_exposures, total_remaining = {}, 0.0
        for account, amount in desired_positions.get(fxpair, {}).items():
            exposure = cash_exposures.get(account, 0.0)
            remaining_exposure = exposure + amount  # Position and exposure cancel since they have opposite sign.

            # Initialize new desired positions.
            changed_desired_positions.setdefault(fxpair, {})[account] = amount

            if np.sign(remaining_exposure) == np.sign(change):
                remaining_exposures[account] = remaining_exposure
                total_remaining += remaining_exposure

        # What fraction of the remaining exposure should be hedged by the accounts where the sign of their exposure
        # matches the sign of the change in liquidity.
        fraction_adjust = change / total_remaining
        for account, diff in remaining_exposures.items():
            # Position is in the opposite direction to exposure.
            changed_desired_positions.setdefault(fxpair, {})[account] -= fraction_adjust * diff

    return changed_desired_positions
