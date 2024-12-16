import uuid
from enum import Enum

from django.db import models
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel
from multiselectfield import MultiSelectField
from phonenumber_field.modelfields import PhoneNumberField

from main.apps.account.models import Company
from main.apps.broker.models import Broker
from main.apps.core.constants import COUNTRY_HELP_TEXT, ADDITIONAL_FIELDS_HELP_TEXT, REGULATORY_HELP_TEXT, \
    PHONE_HELP_TEXT
from main.apps.currency.models import Currency


class Beneficiary(TimeStampedModel):
    # Choices
    class AccountType(models.TextChoices):
        INDIVIDUAL = "individual", _("Individual")
        CORPORATE = "corporate", _("Corporate")

    class Classification(models.TextChoices):
        INDIVIDUAL = "individual", _("Individual")
        BUSINESS = "business", _("Business")
        AEROSPACE_DEFENSE = "aerospace_defense", _("Aerospace and defense")
        AGRICULTURE_AGRIFOOD = "agriculture_agrifood", _("Agriculture and agric-food")
        APPAREL_CLOTHING = "apparel_clothing", _("Apparel / Clothing")
        AUTOMOTIVE_TRUCKING = "automotive_trucking", _("Automotive / Trucking")
        BOOKS_MAGAZINES = "books_magazines", _("Books / Magazines")
        BROADCASTING = "broadcasting", _("Broadcasting")
        BUILDING_PRODUCTS = "building_products", _("Building products")
        CHEMICALS = "chemicals", _("Chemicals")
        DAIRY = "dairy", _("Dairy")
        E_BUSINESS = "e_business", _("E-business")
        EDUCATIONAL_INSTITUTES = "educational_institute", _("Educational Institutes")
        ENVIRONMENT = "environment", _("Environment")
        EXPLOSIVES = "explosives", _("Explosives")
        FISHERIES_OCEANS = "fisheries_oceans", _("Fisheries and oceans")
        FOOD_BEVERAGE_DISTRIBUTION = "food_beverage_distribution", _("Food / Beverage distribution")
        FOOTWEAR = "footwear", _("Footwear")
        FOREST_INDUSTRIES = "forest_industries", _("Forest industries")
        FURNITURE = "furniture", _("Furniture")
        GIFTWARE_CRAFTS = "giftware_crafts", _("Giftware and crafts")
        HORTICULTURE = "horticulture", _("Horticulture")
        HYDROELECTRIC_ENERGY = "hydroelectric_energy", _("Hydroelectric energy")
        ICT = "ict", _("Information and communication technologies")
        INTELLIGENT_SYSTEMS = "intelligent_systems", _("Intelligent systems")
        LIVESTOCK = "livestock", _("Livestock")
        MEDICAL_DEVICES = "medical_devices", _("Medical devices")
        MEDICAL_TREATMENT = "medical_treatment", _("Medical treatment")
        MINERALS_METALS_MINING = "minerals_metals_mining", _("Minerals, metals and mining")
        OIL_GAS = "oil_gas", _("Oil and gas")
        PHARMACEUTICALS_BIOPHARMACEUTICALS = "pharmaceuticals_biopharmaceuticals", _(
            "Pharmaceuticals and biopharmaceuticals")
        PLASTICS = "plastics", _("Plastics")
        POULTRY_EGGS = "poultry_eggs", _("Poultry and eggs")
        PRINTING_PUBLISHING = "printing_publishing", _("Printing / Publishing")
        PRODUCT_DESIGN_DEVELOPMENT = "product_design_development", _("Product design and development")
        RAILWAY = "railway", _("Railway")
        RETAIL = "retail", _("Retail")
        SHIPPING_INDUSTRIAL_MARINE = "shipping_industrial_marine", _("Shipping and industrial marine")
        SOIL = "soil", _("Soil")
        SOUND_RECORDING = "sound_recording", _("Sound recording")
        SPORTING_GOODS = "sporting_goods", _("Sporting goods")
        TELECOMMUNICATIONS_EQUIPMENT = "telecommunications_equipment", _("Telecommunications equipment")
        TELEVISION = "television", _("Television")
        TEXTILES = "textiles", _("Textiles")
        TOURISM = "tourism", _("Tourism")
        TRADEMARKS_LAW = "trademakrs_law", _("Trademarks / Law")
        WATER_SUPPLY = "water_supply", _("Water supply")
        WHOLESALE = "wholesale", _("Wholesale")

    class IdentificationType(models.TextChoices):
        PASSPORT = "passport", _("Passport")
        NATIONAL_ID = "national_id", _("National ID")
        DRIVING_LICENSE = "driving_license", _("Driving License")
        OTHERS = "others", _("Others")
        CPF = "cpf", _("CPF")
        CNPJ = "cnpj", _("CNPJ")

    class PaymentSettlementMethod(models.TextChoices):
        LOCAL = 'local', _('Local')
        SWIFT = 'swift', _('Swift')
        WALLET = 'wallet', _('Wallet')
        CARD = 'card', _('Card')
        PROXY = 'proxy', _('Proxy')

    class BankAccountType(models.TextChoices):
        CURRENT = 'current', _('Current')
        SAVING = 'saving', _('Saving')
        MAESTRA = 'maestra', _('Maestra')
        CHECKING = 'checking', _('Checking')

    class BankAccountNumberType(models.TextChoices):
        IBAN = 'iban', _('IBAN')
        CLABE = 'clabe', _('CLABE')
        ACCOUNT_NUMBER = 'account_number', _('Account Number')

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        SYNCED = "synced", _("Synced")
        PENDING_UPDATE = 'pending_update', _("Pending Update")
        PENDING_DELETE = 'pending_delete', _("Pending Delete")
        DELETED = "deleted", _("Deleted")
        PARTIALLY_SYNCED = "partially_synced", _("Partially Synced")
        PARTIALLY_DELETED = "partially_deleted", _("Partially Deleted")

    class BankRoutingCodeType(models.TextChoices):
        SWIFT = 'swift', _('SWIFT')
        IFSC = 'ifsc', _('IFSC')
        SORT_CODE = 'sort_code', _('SORT Code')
        ACH_CODE = 'ach_code', _('ACH Code')
        BRANCH_CODE = 'branch_code', _('Branch Code')
        BSB_CODE = 'bsb_code', _('BSB Code')
        BANK_CODE = 'bank_code', _('Bank Code')
        ABA_CODE = 'aba_code', _('ABA Code')
        TRANSIT_CODE = 'transit_code', _('Transit Code')
        GENERIC = 'generic', _('Generic')
        WALLET = 'wallet', _('Wallet')
        LOCATION_ID = 'location_id', _('Location ID')
        BRANCH_NAME = 'branch_name', _('Branch Name')
        CNAPS = 'cnaps', _('CNAPS')
        FEDWIRE = 'fedwire', _('Fedwire')
        INTERAC = 'interac', _('Interac')
        CHECK = 'check', _('Check')

    class ProxyType(models.TextChoices):
        MOBILE = 'mobile', _('Mobile')
        UEN = 'uen', _('UEN')
        NRIC = 'nric', _('NRIC')
        VPA = 'vpa', _('VPA')
        ID = 'id', _('ID')
        EMAIL = 'email', _('Email')
        RANDOM_KEY = 'random_key', _('Random Key')
        ABN = 'abn', _('ABN')
        ORGANISATION_ID = 'organization_id', _('Organisation ID')
        PASSPORT = 'passport', _('Passport')
        CORPORATE_REGISTRATION_NUMBER = 'corporate_registration_number', _('Corporate Registration Number')
        ARMY_ID = 'army_id', _('Army ID')

    class RegulatoryBeneficiaryAccountType(models.TextChoices):
        CCAC = 'ccac', _('Checking')
        SVGS = 'svgs', _('Savings')

    class Purpose(models.IntegerChoices):
        INTERCOMPANY_PAYMENT = 1, _('Intercompany Payment')
        PURCHASE_SALE_OF_GOODS = 2, _('Purchase/Sale of Goods')
        PURCHASE_SALE_OF_SERVICES = 3, _('Purchase/Sale of Services')
        PERSONNEL_PAYMENT = 4, _('Personnel Payment')
        FINANCIAL_TRANSACTION = 5, _('Financial Transaction')
        OTHER = 6, _('Other')

    class MonexPurposeDev(Enum):
        OTHER = (1, 'Other')
        GOODS_PURCHASED = (2, 'Payment for Goods Purchased')
        GOODS_EQUIPMENT = (3, 'Payment for Goods Purchased - Equipment')
        GOODS_FINISHED = (4, 'Payment for Goods Purchased - Finished Goods')
        GOODS_MANUFACTURING = (5, 'Payment for Goods Purchased - Manufacturing Materials')
        INTERNATIONAL_PAYROLL = (6, 'Payment for International Payroll')
        SERVICES_PURCHASED = (7, 'Payment for Services Purchased')
        FUND_OVERSEAS = (8, 'Payment to fund Overseas Operations')
        REPATRIATE_ABROAD = (9, 'Repatriate Funds Abroad')
        REPATRIATE_US = (10, 'Repatriate Funds to US')

        @property
        def value(self):
            return self._value_[0]

        @property
        def description(self):
            return self._value_[1]

    class MonexPurposeProd(Enum):
        ADVERTISING_AND_PUBLIC_RELATIONS_PAYMENT = (1, 'Advertising and Public Relations Payment')
        CANADA_POP = (2, 'CANADA POP')
        CHARITABLE_OR_RELIGIOUS_DONATION = (3, 'Charitable or Religious Donation')
        CONSTRUCTION_EXPENSES = (4, 'Construction Expenses')
        EDUCATION_EXPENSES = (5, 'Education Expenses')
        EXPENSE_REIMBURSEMENT = (6, 'Expense Reimbursement')
        FAMILY_MAINTENANCE = (7, 'Family Maintenance')
        INSURANCE_PAYMENT = (8, 'Insurance Payment')
        INVESTMENT_PAYMENT = (9, 'Investment Payment')
        LOAN_PAYMENT = (10, 'Loan Payment')
        MEDICAL_EXPENSES = (11, 'Medical Expenses')
        OTHER = (12, 'Other')
        PAYMENT_FOR_GOODS_PURCHASED = (13, 'Payment for Goods Purchased')
        PAYMENT_FOR_GOODS_PURCHASED__EQUIPMENT = (14, 'Payment for Goods Purchased - Equipment')
        PAYMENT_FOR_GOODS_PURCHASED__FINISHED_GOODS = (15, 'Payment for Goods Purchased - Finished Goods')
        PAYMENT_FOR_GOODS_PURCHASED__MANUFACTURING_MATERIALS = (
        16, 'Payment for Goods Purchased - Manufacturing Materials')
        PAYMENT_FOR_INTERNATIONAL_PAYROLL = (17, 'Payment for International Payroll')
        PAYMENT_FOR_SERVICES_PURCHASED = (18, 'Payment for Services Purchased')
        PAYMENT_TO_FUND_OVERSEAS_OPERATIONS = (19, 'Payment to fund Overseas Operations')
        REAL_ESTATE_PURCHASE = (20, 'Real Estate Purchase')
        RENTAL_PROPERTY_PAYMENT = (21, 'Rental Property Payment')
        REPATRIATE_FUNDS_ABROAD = (22, 'Repatriate Funds Abroad')
        REPATRIATE_FUNDS_TO_US = (23, 'Repatriate Funds to US')
        RESEARCH_AND_DEVELOPMENT_PAYMENT = (24, 'Research and Development Payment')
        ROYALTIES_AND_INTELLECTUAL_PROPERTY_PAYMENT = (25, 'Royalties and Intellectual Property Payment')
        TAX_PAYMENT = (26, 'Tax Payment')
        TRANSFER_TO_OWN_ACCOUNT = (27, 'Transfer to Own Account')

        @property
        def value(self):
            return self._value_[0]

        @property
        def description(self):
            return self._value_[1]

    class CorpayPurpose(Enum):
        PURCHASE_OF_GOODS = ("PURCHASE OF GOOD(S)", "Purchase of Good(s)")
        PURCHASE_PROFESSIONAL_SERVICE = ("PURCHASE PROFESSIONAL SERVICE", "Purchase of Professional Service(s)")
        PROFESSIONAL_FEES_PAYMENT = ("PROFESSIONAL FEES PAYMENT", "Professional fees payment (i.e. legal, accountant)")
        PAYROLL_PERSONNEL_PAYMENT = ("PAYROLL/PERSONNEL PAYMENT", "Payroll/Personnel payment")
        PAYMENT_FOR_A_LOAN_OR_DEPOSIT = ("PAYMENT FOR A LOAN OR DEPOSIT", "Payment for a loan or deposit")
        BILL_PAYMENT = ("BILL PAYMENT", "Bill payment (i.e. credit card, utility)")
        RESEARCH_AND_DEVELOPMENT = ("RESEARCH AND DEVELOPMENT", "Research and Development")
        BUSINESS_VENTURE = ("BUSINESS VENTURE", "Business venture (i.e. merger, acquisition)")
        INTERCOMPANY_PAYMENT = ("INTERCOMPANY PAYMENT", "Intercompany payment")
        CHARITABLE_DONATION = ("CHARITABLE DONATION", "Charitable donation")
        PURCHASE_OF_PROPERTY_REAL_ESTATE = ("PURCHASE OF PROPERTY / REAL ESTATE", "Purchase of property / real estate")
        ESTATE_SETTLEMENT_INHERITANCE = ("ESTATE SETTLEMENT / INHERITANCE", "Estate settlement / Inheritance")
        GOVERNMENT_RELATED_PAYMENT = ("GOVERNMENT RELATED PAYMENT", "Government related payment")
        INVESTMENT_RELATED_PAYMENT = ("INVESTMENT RELATED PAYMENT", "Investment related payment")
        PAYMENT_FAMILY_ASSISTANCE = ("PAYMENT,FAMILY ASSISTANCE", "Payment,Family Assistance")
        MEDICAL_ASSISTANCE = ("MEDICAL ASSISTANCE", "Medical Assistance")
        MEDICAL_CLAIM_REIMBURSEMENT = ("MEDICAL CLAIM REIMBURSEMENT", "Medical Claim Reimbursement")
        REMITTANCE_OF_FUNDS_FROM_ECOMMERCE = ("REMITTANCE OF FUNDS FROM E-COMMERCE", "Remittance of funds from e-commerce")
        IP_TRADEMARK_PATENT_WORK = ("IP TRADEMARK PATENT WORK", "IP Trademark Patent Work")
        TRAVEL_HOSPITALITY = ("TRAVEL HOSPITALITY", "Travel/Hospitality")
        PUBLISHER = ("PUBLISHER", "Publisher")

        @property
        def id(self):
            return self._value_[0]

        @property
        def description(self):
            return self._value_[1]

    # Payment
    destination_country = models.CharField(max_length=2, help_text=COUNTRY_HELP_TEXT)
    destination_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Currency of the destination"
    )

    payment_methods = MultiSelectField(
        choices=PaymentSettlementMethod.choices,
        null=True,
        blank=True,
        help_text="Payment methods"
    )
    settlement_methods = MultiSelectField(
        choices=PaymentSettlementMethod.choices,
        null=True,
        blank=True,
        help_text="Settlement methods"
    )
    preferred_method = models.CharField(
        choices=PaymentSettlementMethod.choices,
        null=True,
        blank=True,
        max_length=11,
        help_text="Preferred payment method"
    )
    payment_reference = models.TextField(help_text="Payment reference", null=True, blank=True)

    # Beneficiary Information
    beneficiary_account_type = models.CharField(choices=AccountType.choices, help_text="Beneficiary account type")
    beneficiary_name = models.TextField(
        help_text="Full name of the account holder. Maximum 100 characters."
    )
    beneficiary_alias = models.TextField(help_text="Beneficiary alias", blank=True, null=True)
    beneficiary_address_1 = models.TextField(help_text="Ex: 123 Main St.", null=True, blank=True)
    beneficiary_address_2 = models.TextField(help_text="Ex: Apt. #4", null=True, blank=True)
    beneficiary_country = models.CharField(max_length=2, help_text=f"The beneficiary's country. {COUNTRY_HELP_TEXT}")
    beneficiary_region = models.TextField(help_text="State, Province, etc.")
    beneficiary_postal = models.TextField(help_text="Postal code")
    beneficiary_city = models.TextField(help_text="City")
    beneficiary_phone = PhoneNumberField(help_text=PHONE_HELP_TEXT, null=True, blank=True)
    beneficiary_email = models.EmailField(help_text="Email address", null=True, blank=True)

    classification = models.CharField(
        choices=Classification.choices,
        help_text="Classification of the beneficiary"
    )

    # Identification
    date_of_birth = models.DateField(null=True, blank=True, help_text="Date of birth")

    identification_type = models.CharField(
        max_length=50,
        choices=IdentificationType.choices,
        blank=True,
        help_text="Type of identification document"
    )
    identification_value = models.CharField(max_length=50, blank=True, help_text="Identification document number")

    # Bank Fields
    bank_account_type = models.CharField(choices=BankAccountType.choices, help_text="Bank account type",
                                         null=True, blank=True)
    bank_code = models.TextField(help_text="Bank code", null=True, blank=True)
    bank_account_number = models.TextField(help_text="Bank account number, IBAN, etc.")
    bank_account_number_type = models.CharField(choices=BankAccountNumberType.choices,
                                                help_text="Bank account number type")
    bank_name = models.TextField(help_text="Bank name")
    bank_country = models.CharField(max_length=2, help_text=COUNTRY_HELP_TEXT)
    bank_region = models.TextField(help_text="State, Province, etc.", blank=True, null=True)
    bank_city = models.TextField(help_text="Bank city")
    bank_postal = models.TextField(help_text="Bank postal code", null=True, blank=True)
    bank_address_1 = models.TextField(help_text="Bank address line 1")
    bank_address_2 = models.TextField(help_text="Bank address line 2", null=True, blank=True)
    bank_branch_name = models.TextField(help_text="Bank Branch Name", null=True, blank=True)
    bank_instruction = models.TextField(help_text="Wiring instruction", null=True, blank=True)
    bank_routing_code_value_1 = models.TextField(help_text="Bank routing code 1", null=True, blank=True)
    bank_routing_code_type_1 = models.CharField(choices=BankRoutingCodeType.choices,
                                                help_text="Bank Routing Code 1 Type", null=True, blank=True)
    bank_routing_code_value_2 = models.TextField(help_text="Bank routing code 2", null=True, blank=True)
    bank_routing_code_type_2 = models.CharField(choices=BankRoutingCodeType.choices,
                                                help_text="Bank Routing Code 2 Type",
                                                null=True, blank=True)
    bank_routing_code_value_3 = models.TextField(help_text="Bank routing code 3", null=True, blank=True)
    bank_routing_code_type_3 = models.CharField(choices=BankRoutingCodeType.choices,
                                                default=BankRoutingCodeType.SWIFT,
                                                help_text="Bank Routing Code 3 Type",
                                                null=True, blank=True)

    # Inter-bank Fields
    inter_bank_account_type = models.CharField(choices=BankAccountType.choices, help_text="Bank account type",
                                               null=True, blank=True)
    inter_bank_code = models.TextField(help_text="Intermediary bank code", null=True, blank=True)
    inter_bank_account_number = models.TextField(help_text="Intermediary bank account number", null=True, blank=True)
    inter_bank_account_number_type = models.CharField(choices=BankAccountNumberType.choices,
                                                      help_text="Intermediary bank account number type",
                                                      null=True, blank=True)
    inter_bank_name = models.TextField(help_text="Intermediary Bank name", null=True, blank=True)
    inter_bank_country = models.TextField(help_text="Intermediary Bank country", null=True, blank=True)
    inter_bank_region = models.TextField(help_text="Intermediary Bank region", null=True, blank=True)
    inter_bank_city = models.TextField(help_text="Intermediary Bank city", null=True, blank=True)
    inter_bank_postal = models.TextField(help_text="Intermediary Bank postal code", null=True, blank=True)
    inter_bank_address_1 = models.TextField(help_text="Intermediary Bank address line 1", null=True, blank=True)
    inter_bank_address_2 = models.TextField(help_text="Intermediary Bank address line 2", null=True, blank=True)
    inter_bank_branch_name = models.TextField(help_text="Intermediary Bank Branch Name", null=True, blank=True)
    inter_bank_instruction = models.TextField(help_text="Intermediary Bank instruction", null=True, blank=True)
    inter_bank_routing_code_value_1 = models.TextField(help_text="Intermediary bank Routing Code 1",
                                                       null=True, blank=True)
    inter_bank_routing_code_type_1 = models.CharField(choices=BankRoutingCodeType.choices,
                                                      help_text="Intermediary bank Routing Code 1 Type",
                                                      null=True, blank=True)
    inter_bank_routing_code_value_2 = models.TextField(help_text="Intermediary bank routing code 2",
                                                       null=True, blank=True)
    inter_bank_routing_code_type_2 = models.CharField(choices=BankRoutingCodeType.choices,
                                                      help_text="Intermediary bank Routing Code 2 Type",
                                                      null=True, blank=True)
    inter_bank_routing_code_value_3 = models.TextField(help_text="Bank routing code 3", null=True, blank=True)
    inter_bank_routing_code_type_3 = models.CharField(choices=BankRoutingCodeType.choices,
                                                default=BankRoutingCodeType.SWIFT,
                                                help_text="Bank Routing Code 3 Type",
                                                null=True, blank=True)

    # Additional Fields
    client_legal_entity = models.CharField(max_length=2, help_text=COUNTRY_HELP_TEXT)
    proxy_type = models.CharField(choices=ProxyType.choices, help_text="The proxy type sent in the payment request",
                                  null=True, blank=True)
    proxy_value = models.TextField(help_text="The proxy value such as VPA, UEN, or mobile number etc.",
                                   null=True, blank=True)
    remitter_beneficiary_relationship = models.TextField(
        help_text="The relationship of the beneficiary with the remitter",
        null=True, blank=True
    )
    further_name = models.TextField(help_text="Further name", null=True, blank=True)
    further_account_number = models.TextField(help_text="Further account number", null=True, blank=True)

    # Internal
    beneficiary_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier of the beneficiary"
    )
    external_id = models.TextField(
        blank=True
    )
    company = models.ForeignKey(Company, on_delete=models.PROTECT, null=True, blank=True,
                                related_name="%(class)s_beneficiary",
                                help_text="The company the beneficiary belongs to")

    status = models.CharField(
        max_length=60,
        default=Status.DRAFT,
        choices=Status.choices,
        help_text="The status of the beneficiary"
    )

    reason = models.TextField(help_text="The reason for deleting the beneficiary", null=True, blank=True)
    additional_fields = models.JSONField(
        null=True,
        blank=True,
        help_text=ADDITIONAL_FIELDS_HELP_TEXT
    )
    regulatory = models.JSONField(
        null=True,
        blank=True,
        help_text=REGULATORY_HELP_TEXT
    )

    default_purpose = models.IntegerField(
        choices=Purpose.choices,
        default=Purpose.OTHER,
        help_text="Beneficiary default payment purpose"
    )

    default_purpose_description = models.TextField(
        null=True,
        help_text="Please be specific, eg. “This company is a supplier of leather goods. Each month we pay this company for wallets and belts”"
    )

    def __str__(self):
        return self.beneficiary_id.__str__()

    class Meta:
        verbose_name = "Beneficiary"
        verbose_name_plural = "Beneficiaries"
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'beneficiary_alias'],
                name='unique_beneficiary_alias_per_company'
            )
        ]

    @staticmethod
    def get_beneficiary_display(beneficiary_id:str) -> str:
        try:
            bene = Beneficiary.objects.get(beneficiary_id=beneficiary_id)
            return f"{bene.beneficiary_name} - {bene.destination_currency.mnemonic}"
        except Beneficiary.DoesNotExist:
            return ''

class BeneficiaryBroker(models.Model):
    beneficiary = models.ForeignKey(
        Beneficiary,
        on_delete=models.CASCADE,
        help_text="The beneficiary associated with this broker"
    )
    broker = models.ForeignKey(
        Broker,
        on_delete=models.CASCADE,
        help_text="The broker associated with this beneficiary"
    )
    broker_beneficiary_id = models.CharField(
        max_length=255,
        help_text="The broker-specific beneficiary ID"
    )
    enabled = models.BooleanField(
        default=True,
        help_text="The beneficiary enable status"
    )
    deleted = models.BooleanField(
        default=False,
        help_text="The brokers's beneficiary deleted status"
    )

    class Meta:
        unique_together = ('beneficiary', 'broker')
        verbose_name = "Beneficiary Broker"
        verbose_name_plural = "Beneficiary Brokers"

    def __str__(self):
        return f"{self.beneficiary} - {self.broker}"


class BeneficiaryFieldMapping(models.Model):
    brokers = models.ManyToManyField(
        Broker,
        help_text="The brokers associated with the field mapping"
    )
    beneficiary_field = models.CharField(
        max_length=100,
        help_text="The field name in the beneficiary model",
    )
    broker_field = models.CharField(
        max_length=100,
        help_text="The corresponding field name in the broker's API"
    )

    def __str__(self):
        return f"{self.beneficiary_field} - {self.broker_field}"


class BeneficiaryFieldConfig(models.Model):
    brokers = models.ManyToManyField(
        Broker,
        help_text="The brokers associated with the field configuration"
    )
    field_name = models.CharField(
        max_length=100,
        help_text="The field name"
    )
    hidden = models.BooleanField(
        default=False,
        help_text="Indicates whether the field should be hidden"
    )
    validation_rule = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Validation rule (regex) for the field"
    )
    description = models.TextField(
        null=True,
        blank=True,
        help_text="Description of the field"
    )
    is_required = models.BooleanField(
        default=False,
        help_text="Indicates whether the field is required"
    )
    type = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text="The field data type"
    )


class BeneficiaryValueMapping(models.Model):
    field_mapping = models.ForeignKey(
        BeneficiaryFieldMapping,
        on_delete=models.CASCADE,
        help_text="The field mapping associated with this value mapping"
    )
    internal_value = models.CharField(
        max_length=100,
        help_text="The internal value"
    )
    broker_value = models.CharField(
        max_length=100,
        help_text="The broker-specific value"
    )

    class Meta:
        unique_together = ('field_mapping', 'internal_value', 'broker_value')
        verbose_name = "Beneficiary Value Mapping"
        verbose_name_plural = "Beneficiary Value Mappings"

    def __str__(self):
        return f"{self.field_mapping} - {self.internal_value} -> {self.broker_value}"


class BeneficiaryDefaults(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    beneficiary = models.ForeignKey(Beneficiary, on_delete=models.CASCADE)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)


class BeneficiaryBrokerSyncResult(models.Model):
    beneficiary = models.ForeignKey(Beneficiary, null=True, on_delete=models.CASCADE)
    broker = models.ForeignKey(Broker, null=True, on_delete=models.CASCADE)
    last_sync = models.DateTimeField(help_text="Last beneficiary broker sync", null=True)
    sync_errors = models.TextField(help_text="Any Sync error from the last attempt", null=True)
