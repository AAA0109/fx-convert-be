DELIVERY_METHODS = (
    ('W', 'Wire'),
    ('E', 'iACH'),
    ('C', 'FXBalance')
)

SORT_DIRECTIONS = (
    ('asc', 'Ascending'),
    ('desc', 'Descending')
)

BENEFICIARY_CLASSIFICATIONS = (
    ('Business', 'Business'),
    ('Individual', 'Individual')
)

BENEFICIARY_PAYMENT_METHODS = (
    ('W', 'Wire'),
    ('E', 'iACH')
)

BENEFICIARY_STATUSES = (
    ('A', 'Active'),
    ('T', 'Inactive')
)

SETTLEMENT_ACCOUNT_DELIVERY_METHODS = (
    ('W', 'Wire'),
    ('E', 'iACH')
)

PICKLIST_TYPES = (
    ('AnnualVolumeRange', 'Annual Volume Range'),
    ('ApplicantType', 'Applicant Type'),
    ('BusinessType', 'Business Type'),
    ('PurposeOfTransaction', 'Purpose of Transaction'),
    ('TradeVolumeRange', 'Trade Volume Range'),
    ('NatureOfBusiness', 'Nature Of Business')
)

BALANCE_TYPE_FROM = (
    ('fx_balance', 'Fx Balance'),
    ('settlement_account', 'Settlement Account')
)

BALANCE_TYPE_TO = (
    ('fx_balance', 'Fx Balance'),
    ('settlement_account', 'Settlement Account'),
    ('beneficiary', 'Beneficiary')
)

FORWARD_TYPE = (
    ('C', 'Closed Contract'),
    ('O', 'Open Contract')
)

RATE_OPERATION = (
    ('Multiply', 'Multiply'),
    ('Divide', 'Divide')
)

MASS_PAYMENT_METHODS = (
    ('Wire', 'Wire'),
    ('EFT', 'EFT'),
    ('StoredValue', 'FX Balance')
)
