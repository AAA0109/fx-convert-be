from main.apps.currency.models import FxPair
from main.apps.currency.models import Currency
import logging
from typing import Sequence, Optional

logger = logging.getLogger(__name__)


def create_currency(mnemonic: str, name: Optional[str] = None, symbol: Optional[str] = None):
    """
    Create a currency from its mnemonic. Note that this leaves most currency fields null (except for mnemonic)
    """
    from main.apps.currency.models import Currency
    status, currency = Currency.create_currency(mnemonic=mnemonic, name=name, symbol=symbol)
    if status.is_error():
        logger.error(f"Error creating currency for '{mnemonic}': {status.message}")
    return currency


def create_fx_pairs(fxpairs: Sequence[str], allow_cross_currency_pairs: bool = False, add_reverse_pairs: bool = False):
    """
    Create all the listed FX pairs. The FxPairs must be represented as strings in either "[Base][Quote]"
    or "[Base]/[Quote]" form, where [Base] and [Quote] are three letter currency mnemonics. If any currency does not
    already exist, it is added to the DB first.
    If allow_cross_currency_pairs is false, any Fx where neither of the currencies is "USD" is disallowed. This is
    mainly to prevent misspellings of currencies, if you have to enter many Fx mnemonics, it is easy to mistype some,
    and this is one way to catch that.
    """
    for fxpair in fxpairs:
        fx = FxPair.get_pair(fxpair)
        if not fx:
            logger.debug(f"The pair '{fxpair}' does not exist yet, creating.")
            if len(fxpair) == 6:
                base, quote = fxpair[:3], fxpair[3:]
            elif len(fxpair) == 7 and fxpair[3] == '/':
                base, quote = fxpair[:3], fxpair[4:]
            else:
                logger.warning(f"FX pair format not detectable for '{fxpair}', skipping.")
                continue

            if base != "USD" and quote != "USD":
                logger.warning(f"Neither the base or quote currency were USD.")
                if not allow_cross_currency_pairs:
                    logger.debug(f"Not allowing cross-currency pairs. Skipping '{fxpair}'.")
                    continue

            base_currency = Currency.get_currency(base)
            quote_currency = Currency.get_currency(quote)

            if not base_currency:
                logger.debug(f"Base currency '{base}' does not exist yet, creating.")
                base_currency = create_currency(base)
            if not quote_currency:
                logger.debug(f"Quote currency '{quote}' does not exist yet, creating.")
                quote_currency = create_currency(quote)

            status, fx = FxPair.create_fxpair(base_currency, quote_currency)
            if status.is_error():
                logger.error(f"Error creating FxPair for '{fxpair}': {status.message}")
            else:
                logger.debug(f"Successfully created FxPair '{fx}'.")

            if add_reverse_pairs:
                logger.debug(f"Adding reverse pair '{quote_currency}/{base_currency}'")
                status, fx = FxPair.create_fxpair(quote_currency, base_currency)
                if status.is_error():
                    logger.error(f"Error creating FxPair for '{quote_currency}/{base_currency}': {status.message}")
                elif status.is_no_change():
                    logger.debug(f"Reverse pair already existed, nothing to add.")
                else:
                    logger.debug(f"Successfully created FxPair '{fx}'.")

        else:
            logger.debug(f"The pair '{fxpair}' already exists, not creating.")

            fxrev = FxPair.get_inverse_pair(pair=fx)
            if not fxrev:
                base_currency = fx.base_currency
                quote_currency = fx.quote_currency
                logger.debug(f"Adding reverse pair '{quote_currency}/{base_currency}'")
                status, fx = FxPair.create_fxpair(quote_currency, base_currency)
                if status.is_error():
                    logger.error(f"Error creating FxPair for '{quote_currency}/{base_currency}': {status.message}")
                else:
                    logger.debug(f"Successfully created FxPair '{fx}'.")
            else:
                logger.debug(f"Reverse pair '{fxrev}' already exists, not creating.")
