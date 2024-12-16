from django.utils.translation import gettext_lazy as _

CURRENCY_HELP_TEXT = _("ISO 4217 Standard 3-Letter Currency Code")
VALUE_DATE_HELP_TEXT = (
    "The date when the transaction will settle. "
    "Defaults to the following business day if settlement cannot occur on the provided value_date."
)
LOCK_SIDE_HELP_TEXT = _("ISO 4217 Standard 3-Letter Currency Code used to indicate "
                        "which amount you are defining the value of. The non-lock_side amount will be calculated."
                        )
TARGET_VARIANCE_HELP_TEXT = _("the targeted variance (%) between the executed rate and today’s rate")
RISK_BEFORE_HEDGE_HELP_TEXT = _("the 95th percentile value at risk of the total position amount")
REMAINING_RISK_AFTER_HEDGE_HELP_TEXT = _("the 95th percentile value at risk of "
                                         "the position that has not yet been hedged")
MAX_COST_HELP_TEXT = _("maximum cost in the base currency if the strategy fully hedges the position")
COUNTRY_HELP_TEXT = _('This field accepts the '
                      '<a href="https://docs.pangea.io/reference/currency-and-country-codes"> '
                      'ISO-2 country code</a>')
ADDITIONAL_FIELDS_HELP_TEXT = _("Additional broker-specific fields as key-value pairs")
REGULATORY_HELP_TEXT = _("The fields and corresponding values needed to satisfy regulatory requirements for "
                         "the destination country.")
PHONE_HELP_TEXT = _("Phone number with country code, eg. +1-415-333-4444")
BENEFICIARY_IDENTIFIER_HELP_TEXT = _(
    "A unique identifier for the beneficiary. Can be either the beneficiary_id (UUID) or beneficiary_alias (string).")
