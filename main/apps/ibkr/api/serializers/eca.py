from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from localflavor.us.us_states import STATE_CHOICES
from rest_framework import serializers

from main.apps.core.serializers.common import HDLDateField
from main.apps.ibkr.api.serializers.fields.country import IBCountryField
from main.apps.ibkr.models import Application


class IBOrganizationTaxResidencySerializer(serializers.Serializer):
    tin = serializers.CharField()
    country = IBCountryField(default='US', country_dict=True)


class IBPlaceOfBusinessSerializer(serializers.Serializer):
    country = IBCountryField(default='US', country_dict=True)
    state = serializers.ChoiceField(choices=STATE_CHOICES)
    city = serializers.CharField()
    postal_code = serializers.CharField()
    street_1 = serializers.CharField()
    street_2 = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class IBMailingAddressSerializer(serializers.Serializer):
    country = IBCountryField(default='US', country_dict=True)
    state = serializers.ChoiceField(choices=STATE_CHOICES)
    city = serializers.CharField()
    postal_code = serializers.CharField()
    street_1 = serializers.CharField()
    street_2 = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class IBOrganizationIdentificationSerializer(serializers.Serializer):
    formation_country = IBCountryField(default='US', country_dict=True)
    identification = serializers.CharField(default='11122333')
    identification_country = IBCountryField(default='US', country_dict=True)
    name = serializers.CharField()
    same_mail_address = serializers.BooleanField()
    place_of_business = IBPlaceOfBusinessSerializer()
    mailing_address = IBMailingAddressSerializer(required=False)


class IBAssociatedIndividualTitleSerializer(serializers.Serializer):
    CODES = [
        ('DIRECTOR', 'DIRECTOR'),
        ('OTHER OFFICER', 'OTHER OFFICER'),
        ('SECRETARY', 'SECRETARY'),
        ('SIGNATORY', 'SIGNATORY'),
        ('CEO', 'CEO'),
        ('OWNER', 'OWNER'),
        ('Grantor', 'Grantor'),
        ('Trustee', 'Trustee')
    ]
    code = serializers.ChoiceField(choices=CODES)


class IBAssociatedIndividualResidenceSerializer(serializers.Serializer):
    country = IBCountryField(default='US', country_dict=True)
    state = serializers.ChoiceField(choices=STATE_CHOICES)
    city = serializers.CharField()
    postal_code = serializers.CharField()
    street_1 = serializers.CharField()
    street_2 = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class IBAssociatedIndividualMailingAddressSerializer(serializers.Serializer):
    country = IBCountryField(default='US', country_dict=True)
    state = serializers.ChoiceField(choices=STATE_CHOICES)
    city = serializers.CharField()
    postal_code = serializers.CharField()
    street_1 = serializers.CharField()
    street_2 = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class IBAssociatedIndividualIdentificationSerializer(serializers.Serializer):
    issuing_country = IBCountryField(default='US', country_dict=True)
    legal_residence_country = IBCountryField(default='US', country_dict=True)
    legal_residence_state = serializers.ChoiceField(choices=STATE_CHOICES)
    ssn = serializers.CharField()
    citizenship = IBCountryField(default='US', country_dict=True)


class IBAssociatedIndividualNameSerializer(serializers.Serializer):
    SALUTATIONS = [
        ('Mr.', 'Mr.'),
        ('Mrs.', 'Mrs.'),
        ('Ms.', 'Ms.'),
        ('Dr.', 'Dr.'),
        ('Mx.', 'Mx.'),
        ('Ind.', 'Ind.'),
    ]
    first = serializers.CharField()
    middle = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    last = serializers.CharField()
    salutation = serializers.ChoiceField(choices=SALUTATIONS)


class IBAssociatedIndividualTaxResidencySerializer(serializers.Serializer):
    TIN_TYPE = [
        ('SSN', 'SSN'),
        ('NonUS_NationId', 'NonUS_NationId'),
        ('EIN', 'EIN')
    ]
    tin = serializers.CharField()
    tin_type = serializers.ChoiceField(choices=TIN_TYPE, default='SSN')
    country = IBCountryField(default='US', country_dict=True)


class IBAssociatedIndividualSerializer(serializers.Serializer):
    name = IBAssociatedIndividualNameSerializer()
    dob = serializers.DateField(format='iso-8601')
    residence = IBAssociatedIndividualResidenceSerializer()
    mailing_address = IBAssociatedIndividualMailingAddressSerializer(required=False)
    email = serializers.EmailField()
    identification = IBAssociatedIndividualIdentificationSerializer()
    tax_residencies = serializers.ListSerializer(child=IBAssociatedIndividualTaxResidencySerializer())
    authorized_person = serializers.BooleanField()
    external_id = serializers.CharField(required=False)
    title = IBAssociatedIndividualTitleSerializer()


class IBAssociatedEntitiesSerializer(serializers.Serializer):
    associated_individual = serializers.ListSerializer(child=IBAssociatedIndividualSerializer())


class IBOrganizationSerializer(serializers.Serializer):
    US_TAX_PURPOSE_TYPES = [
        ('C', 'Corporation'),
        ('P', 'Partnership'),
        ('E', 'Disregarded Entity')
    ]
    ORGANIZATION_TYPES = [
        ('LLC', 'LLC'),
        ('CORPORATION', 'CORPORATION'),
        ('PARTNERSHIP', 'PARTNERSHIP'),
        ('UNINCORPORATED BUSINESS', 'UNINCORPORATED BUSINESS')
    ]
    us_tax_purpose_type = serializers.ChoiceField(choices=US_TAX_PURPOSE_TYPES, default='C')
    type = serializers.ChoiceField(choices=ORGANIZATION_TYPES, default='CORPORATION')
    identification = IBOrganizationIdentificationSerializer()
    tax_residencies = serializers.ListSerializer(child=IBOrganizationTaxResidencySerializer())
    associated_entities = IBAssociatedEntitiesSerializer()


class IBCustomerSerializer(serializers.Serializer):
    CUSTOMER_TYPES = [
        ('INDIVIDUAL', 'INDIVIDUAL'),
        ('JOINT', 'JOINT'),
        ('TRUST', 'TRUST'),
        ('ORG', 'ORG'),
    ]
    email = serializers.EmailField()
    external_id = serializers.CharField(required=False)
    md_status_nonpro = serializers.BooleanField(default=False)
    prefix = serializers.CharField(required=False)
    type = serializers.ChoiceField(choices=CUSTOMER_TYPES, default='ORG')
    organization = IBOrganizationSerializer()


class IBFeesSerializer(serializers.Serializer):
    template_name = serializers.CharField(default='test123')


class IBAccountSerializer(serializers.Serializer):
    CURRENCIES = [
        ('AUD', 'AUD'),
        ('DKK', 'DKK'),
        ('ILS', 'ILS'),
        ('NZD', 'NZD'),
        ('TRY', 'TRY'),
        ('CAD', 'CAD'),
        ('EUR', 'EUR'),
        ('JPY', 'JPY'),
        ('PLN', 'PLN'),
        ('USD', 'USD'),
        ('CHF', 'CHF'),
        ('GBP', 'GBP'),
        ('KRW', 'KRW'),
        ('RUB', 'RUB'),
        ('ZAR', 'ZAR'),
        ('CNH', 'CNH'),
        ('HKD', 'HKD'),
        ('MXN', 'MXN'),
        ('SEK', 'SEK'),
        ('CZK', 'CZK'),
        ('HUF', 'HUF'),
        ('NOK', 'NOK'),
        ('SGD', 'SGD'),
    ]
    MARGIN = [
        ('CASH', 'Cash'),
        ('MARGIN', 'Margin'),
        ('REGT', 'RegT'),
        ('PORTFOLIOMARGIN', 'PortfolioMargin'),
    ]
    base_currency = serializers.ChoiceField(choices=CURRENCIES, default='USD')
    external_id = serializers.CharField(required=False)
    margin = serializers.ChoiceField(choices=MARGIN, default='CASH')
    multicurrency = serializers.BooleanField()
    fees = IBFeesSerializer()


class IBAccountsSerializer(serializers.Serializer):
    accounts = serializers.ListSerializer(child=IBAccountSerializer())


class IBUserSerializer(serializers.Serializer):
    external_individual_id = serializers.CharField(required=False)
    external_user_id = serializers.CharField(required=False)
    prefix = serializers.CharField(required=False)


class IBApplicationSerializer(serializers.Serializer):
    customers = serializers.ListSerializer(child=IBCustomerSerializer())
    accounts = serializers.ListSerializer(child=IBAccountSerializer())
    users = serializers.ListSerializer(child=IBUserSerializer())


class IBApplicationsSerializer(serializers.Serializer):
    application = serializers.ListSerializer(child=IBApplicationSerializer())


class IBApplicationsSuccessResponseSerializer(serializers.Serializer):
    status = serializers.CharField()


class IBApplicationsErrorResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    errors = serializers.ListSerializer(child=serializers.CharField())


class IBAccountStatusSerializer(serializers.Serializer):
    dateStarted = serializers.DateTimeField()
    acctId = serializers.CharField()
    description = serializers.CharField()
    STATUS = [
        ('A', 'Abandoned'),
        ('N', 'New Account/Not Yet Open'),
        ('O', 'Open'),
        ('C', 'Closed'),
        ('P', 'Pending'),
        ('R', 'Rejected')
    ]
    status = serializers.ChoiceField(choices=STATUS)
    state = serializers.CharField(required=False)


class IBAccountStatusSingleSerializer(serializers.Serializer):
    accountId = serializers.CharField()
    isError = serializers.BooleanField()
    description = serializers.CharField()
    status = serializers.CharField()


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Filter by status",
            value={
                "status": "O"
            }
        ),
        OpenApiExample(
            "Filter by start & end date",
            value={
                "start_date": "2021-01-13",
                "end_date": "2023-01-13"
            }
        ),
        OpenApiExample(
            "Filter by start & end date and status",
            value={
                "start_date": "2021-01-13",
                "end_date": "2023-01-13",
                'status': "O"
            }
        )
    ]
)
class IBAccountStatusRequestSerializer(serializers.Serializer):
    start_date = HDLDateField(required=False)
    end_date = HDLDateField(required=False)
    status = serializers.ChoiceField(required=False, choices=IBAccountStatusSerializer.STATUS,
                                     help_text="A=Abandoned, "
                                               "N=New Account / Not Yet Open, "
                                               "O=Open, "
                                               "C=Closed, "
                                               "P=Pending, "
                                               "R=Rejected")


class IBAccountStatusSummarySerializer(serializers.Serializer):
    A = serializers.IntegerField(required=False, allow_null=True)
    C = serializers.IntegerField(required=False, allow_null=True)
    N = serializers.IntegerField(required=False, allow_null=True)
    O = serializers.IntegerField(required=False, allow_null=True)


class IBAccountStatusesResponseSerializer(serializers.Serializer):
    summary = IBAccountStatusSummarySerializer(required=False)
    data = serializers.ListSerializer(child=IBAccountStatusSerializer())
    timestamp = serializers.DateTimeField()


class IBAccountStatusResponseSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    status = IBAccountStatusSingleSerializer(many=True)


class CreateECASSOSerializer(serializers.Serializer):
    credential = serializers.CharField()
    ip = serializers.IPAddressField()
    ACTIONS = [
        ('transfer_funds', 'TransferFunds'),
        ('wire_withdrawal', 'WireWithdrawals'),
        ('ach_withdrawal', 'ACHWithdrawals'),
        ('ach_deposit', 'ACHDeposits'),
        ('transfer_position', 'TransferPositions'),
        ('transaction_history', 'TransferHistory'),
        ('statement', 'Statement')
    ]
    action = serializers.ChoiceField(required=False, choices=ACTIONS)


class CreateECASSOResponseSerializer(serializers.Serializer):
    url = serializers.CharField()


class TasksRequestSerialiezr(serializers.Serializer):
    broker_account_id = serializers.CharField()
    start_date = HDLDateField(required=False)
    end_date = HDLDateField(required=False)
    form_number = serializers.IntegerField(required=False)


class PendingTaskSerializer(serializers.Serializer):
    isRequiredForTrading = serializers.BooleanField()
    isOnlineTask = serializers.BooleanField()
    formNumber = serializers.CharField()
    formName = serializers.CharField()
    action = serializers.CharField()
    isRequiredForApproval = serializers.BooleanField()
    taskNumber = serializers.IntegerField()


class PendingTasksResponseSerializer(serializers.Serializer):
    pendingTasks = PendingTaskSerializer(many=True, required=False)
    isError = serializers.BooleanField()
    isPendingTaskPresent = serializers.BooleanField()
    acctId = serializers.CharField()
    description = serializers.CharField()
    status = serializers.CharField()
    error = serializers.CharField(required=False)


class RegistrationTaskSerializer(serializers.Serializer):
    dateComplete = serializers.DateTimeField(required=False)
    formNumber = serializers.CharField()
    formName = serializers.CharField()
    action = serializers.CharField()
    isRequiredForApproval = serializers.BooleanField()
    state = serializers.CharField(required=False)
    isComplete = serializers.BooleanField()


class RegistrationTasksResponseSerializer(serializers.Serializer):
    registrationTasks = RegistrationTaskSerializer(many=True, required=False)
    isError = serializers.BooleanField()
    dateStarted = HDLDateField()
    isRegistrationTaskPresent = serializers.BooleanField()
    acctId = serializers.CharField()
    description = serializers.CharField()
    status = serializers.CharField()
    error = serializers.CharField(required=False)


class IbkrApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = '__all__'
