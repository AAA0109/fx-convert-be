from main.apps.core.constants import CURRENCY_HELP_TEXT, COUNTRY_HELP_TEXT

CORPAY_FIELD_CONFIG = [
    {
        'field_name': 'templateIdentifier',
        'hidden': True,
        'validation_rule': '^.{1,50}$',
        'description': "The client-assigned template identifier. This value should match the 'clientIntegrationId' in "
                       "the URL. The value in this field is returned in the 'beneIdentifier' "
                       "field when you run GET View Bene.",
        'is_required': False,
        'type': ''
    },
    {
        'field_name': 'sendPayTracker',
        'hidden': True,
        'validation_rule': r'^(true|false)$',
        'description': 'Specifies whether to send an email alert to the beneficiary whenever a payment is released = '
                       '[\'true\', \'false\'].',
        'is_required': False,
        'type': ''
    },
    {
        'field_name': 'ibanDigits',
        'hidden': True,
        'validation_rule': r'^\d{1,34}$',
        'description': 'The bank\'s IBAN number. The IBAN accurately identifies the correct bank and bank account.',
        'is_required': False,
        'type': ''
    },
    {
        'field_name': 'ibanEnabled',
        'hidden': True,
        'validation_rule': r'^(true|false)$',
        'description': 'Indicates whether IBAN is enabled for the beneficiary.',
        'is_required': False,
        'type': ''
    },
    {
        'field_name': 'swiftBicCode',
        'hidden': True,
        'validation_rule': r'^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$',
        'description': 'The unique identifier for the bank or financial institution.',
        'is_required': False,
        'type': ''
    },
    {
        'field_name': 'internalPaymentAlert',
        'hidden': True,
        'validation_rule': r'^.+@.+\..+$',
        'description': 'Internal email addresses to notify when a payment is made to this beneficiary.',
        'is_required': False,
        'type': ''
    },
    {
        'field_name': 'externalPaymentAlert',
        'hidden': True,
        'validation_rule': r'^.+@.+\..+$',
        'description': 'External email addresses to notify when a payment is made to this beneficiary.',
        'is_required': False,
        'type': ''
    },
    {
        'field_name': 'accountHolderPhoneNumber',
        'hidden': False,
        'validation_rule': r'^\+?(?:[0-9] ?){6,14}[0-9]$',
        'description': "The beneficiary's phone number. Written in E.164 format +12345678901",
        'is_required': False,
        'type': ''
    }
]

NIUM_FIELD_CONFIG = [
    {
        'field_name': 'beneficiaryCardExpiryDate',
        'hidden': True,
        'validation_rule': r'^\d{4}-\d{2}-\d{2}$',
        'description': 'This field accepts the expiry date of the card.',
        'is_required': False,
        'type': ''
    },
    {
        'field_name': 'beneficiaryCardIssuerName',
        'hidden': True,
        'validation_rule': r'^.{1,100}$',
        'description': 'This field accepts the issuer name of the card.',
        'is_required': False,
        'type': ''
    },
    {
        'field_name': 'beneficiaryCardToken',
        'hidden': True,
        'validation_rule': r'^.{1,100}$',
        'description': 'This field accepts the system-generated token number to '
                       'identify the card stored at NIUM\'s platform.',
        'is_required': False,
        'type': ''
    },
    {
        'field_name': 'beneficiaryContactNumber',
        'hidden': False,
        'validation_rule': r'^\+?(?:[0-9] ?){6,14}[0-9]$',
        'description': "The beneficiary's phone number. Written in E.164 format +12345678901",
        'is_required': False,
        'type': ''
    }
]

MONEX_FIELD_CONFIG = [
    {
        'field_name': 'id',
        'hidden': True,
        'validation_rule': None,
        'description': 'An ID of the bene that is being updated, skip this field, if a new bene is created/added.',
        'is_required': False,
        'type': 'integer'
    },
    {
        'field_name': 'isEnabled',
        'hidden': True,
        'validation_rule': None,
        'description': 'Is Bene enabled, skip this field, if a new bene is created/added.',
        'is_required': False,
        'type': 'boolean'
    },
    {
        'field_name': 'isIndividual',
        'hidden': True,
        'validation_rule': None,
        'description': 'If `true`, the bene is Individual, otherwise - the bene is Corporate.',
        'is_required': False,
        'type': 'boolean'
    },
    {
        'field_name': 'mainBank.key',
        'hidden': True,
        'validation_rule': None,
        'description': 'A unique identifier of the data object',
        'is_required': False,
        'type': 'string'
    },
    {
        'field_name': 'metaFields',
        'hidden': True,
        'validation_rule': None,
        'description': 'Additional info on the default payment purpose',
        'is_required': False,
        'type': 'object'
    },
    {
        'field_name': 'purposeDescription',
        'hidden': False,
        'validation_rule': None,
        'description': 'Additional info on the default payment purpose',
        'is_required': True,
        'type': 'string'
    },
    {
        'field_name': 'purposeId',
        'hidden': False,
        'validation_rule': None,
        'description': 'A default payment purpose ID',
        'is_required': True,
        'type': 'integer'
    },
    {
        'field_name': 'currencyId',
        'hidden': False,
        'validation_rule': None,
        'description': CURRENCY_HELP_TEXT,
        'is_required': False,
        'type': 'string'
    },
    {
        'field_name': 'countryId',
        'hidden': False,
        'validation_rule': None,
        'description': COUNTRY_HELP_TEXT,
        'is_required': False,
        'type': 'string'
    },
    {
        'field_name': 'mainBank.countryId',
        'hidden': False,
        'validation_rule': None,
        'description': COUNTRY_HELP_TEXT,
        'is_required': False,
        'type': 'string'
    },
    {
        'field_name': 'interBank.countryId',
        'hidden': False,
        'validation_rule': None,
        'description': COUNTRY_HELP_TEXT,
        'is_required': False,
        'type': 'string'
    },
    {
        'field_name': 'nickname',
        'hidden': False,
        'validation_rule': None,
        'description': "Beneficiary alias",
        'is_required': True,
        'type': 'string'
    },
    {
        'field_name': 'mainBank.accountNumber',
        'hidden': False,
        'validation_rule': None,
        'description': 'Bank account number, IBAN, etc.',
        'is_required': True,
        'type': 'string'
    },
    {
        'field_name': 'mainBank.accountNumber',
        'hidden': False,
        'validation_rule': None,
        'description': 'Bank account number, IBAN, etc.',
        'is_required': False,
        'type': 'string'
    }
]
