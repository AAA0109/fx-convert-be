from typing import Optional

import pytz
from rest_framework import serializers

from main.apps.account.api.serializers.account import AccountSummarySerializer
from main.apps.account.api.serializers.installment import InstallmentSerializer
from main.apps.account.models import CashFlow, CashFlowNote, DraftCashFlow, InstallmentCashflow, Account
from main.apps.core.serializers.action_status_serializer import ActionStatusSerializer
from main.apps.currency.api.serializers.models.currency import CurrencySerializer
from main.apps.currency.models import Currency
from main.apps.hedge.api.serializers.fx_forward import FxForwardSerializer, DraftFxForwardSerializer


# ====================================================================
#  CashFlow serializers
# ====================================================================


class DraftCashflowSerializer(serializers.ModelSerializer):
    """
    A serializer for the DraftCashFlow model.

    Note that date fields should be be in the format YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z]
    """

    currency = serializers.CharField(source='currency.mnemonic')

    calendar = serializers.ChoiceField(required=False,
                                       choices=[(cal.value, cal.name) for cal in CashFlow.CalendarType],
                                       default=CashFlow.CalendarType.NULL_CALENDAR.value)
    # Note that a user cannot specify a cashflow id to assign this draft to. Instead, they should rely on the
    # endpoint /api/accounts/{account_id}/cashflows/drafts/ to create a draft of an existing cashflow.
    cashflow_id = serializers.SerializerMethodField(required=False, read_only=True)

    installment_id = serializers.IntegerField(required=False, read_only=False, allow_null=True)
    account_id = serializers.IntegerField(required=False, read_only=False, allow_null=True)

    action = serializers.ChoiceField(required=True,
                                     choices=[(action.value, action.name) for action in DraftCashFlow.Action])

    is_forward = serializers.BooleanField(default=False)

    draft_fx_forward_id = serializers.SerializerMethodField(required=False, read_only=True)

    booked_rate = serializers.FloatField(read_only=True)
    booked_base_amount = serializers.FloatField(read_only=True)
    booked_cntr_amount = serializers.FloatField(read_only=True)

    class Meta:
        model = DraftCashFlow
        fields = [
            'id',
            'date',
            'end_date',
            'currency',
            'amount',
            'created',
            'modified',
            'name',
            'description',
            'periodicity',
            'calendar',
            'roll_convention',
            'installment_id',
            'cashflow_id',
            'account_id',
            'action',
            'is_forward',
            'draft_fx_forward_id',
            'indicative_rate',
            'indicative_base_amount',
            'indicative_cntr_amount',
            'booked_rate',
            'booked_base_amount',
            'booked_cntr_amount'
        ]

        read_only_fields = ['id', 'created', 'modified', 'cashflow_id', 'is_forward']

    def get_cashflow_id(self, draft: DraftCashFlow) -> Optional[int]:
        """
        Returns the id of the cashflow this draft is associated with.
        :param draft: The draft object.
        :return: The id of the cashflow this draft is associated with if this cashflow is associated with one.
        """
        try:
            return draft.cf_draft.get().id
        except CashFlow.DoesNotExist:
            return None

    def get_draft_fx_forward_id(self, draft: DraftCashFlow) -> Optional[int]:
        draft_fx_forward_positions = draft.draftfxforwardposition_set.all()

        if draft.installment is not None:
            installment_positions = draft.installment.draftfxforwardposition_set.all()
            if installment_positions.exists():
                return installment_positions.first().pk

        if draft_fx_forward_positions.exists():
            return draft_fx_forward_positions.first().pk

        return None

    def validate_amount(self, value):
        if value == 0:
            raise serializers.ValidationError(f"Cash flow amount cannot be zero")
        return value

    # Note that we don't need pub/sub here so we just directly use the create method.
    def create(self, validated_data):
        """
        Create a draft cashflow.
        :param validated_data: A dictionary of the fields.
        :return: A draft cashflow object
        """
        cny = Currency.get_currency(currency=validated_data['currency']['mnemonic'])
        if validated_data.get('installment_id', None):
            installment = InstallmentCashflow.get_installment(self.context['request'].user.company,
                                                              validated_data['installment_id'])
        else:
            installment = None
        if validated_data.get('account_id', None):
            account = Account.get_account(validated_data['account_id'])
        else:
            account = None

        return DraftCashFlow.objects.create(date=validated_data['date'],
                                            end_date=validated_data.get('end_date', None),
                                            currency=cny,
                                            amount=validated_data.get('amount', 0),
                                            name=validated_data.get('name', None),
                                            description=validated_data.get('description', None),
                                            periodicity=validated_data.get('periodicity', None),
                                            calendar=validated_data.get('calendar',
                                                                        CashFlow.CalendarType.NULL_CALENDAR),
                                            roll_convention=validated_data.get('roll_convention', None),
                                            company=self.context['request'].user.company,
                                            installment=installment,
                                            account=account,
                                            action=validated_data.get('action', ),
                                            indicative_rate=validated_data.get('indicative_rate'),
                                            indicative_base_amount=validated_data.get('indicative_base_amount'),
                                            indicative_cntr_amount=validated_data.get('indicative_cntr_amount')
                                            )

    def update(self, instance: DraftCashFlow, validated_data: dict):
        """
        Update a draft cashflow.
        :param instance: The draft cashflow object to update.
        :param validated_data: A dictionary of the fields to update.
        :return: the updated cashflow object.
        """
        cny = Currency.get_currency(currency=validated_data.get('currency', {})
                                    .get('mnemonic', instance.currency.mnemonic))
        instance.date = validated_data.get('date', instance.date)
        instance.end_date = validated_data.get('end_date', instance.end_date)
        instance.currency = cny
        instance.amount = validated_data.get('amount', instance.amount)
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.periodicity = validated_data.get('periodicity', instance.periodicity)
        instance.calendar = validated_data.get('calendar', instance.calendar)
        instance.roll_convention = validated_data.get('roll_convention', instance.roll_convention)
        installment_id = validated_data.get('installment_id',
                                            instance.installment.id if instance.installment else None)
        if installment_id:
            instance.installment = InstallmentCashflow.get_installment(self.context['request'].user.company,
                                                                       installment_id)
        if validated_data.get('account_id', None):
            account = Account.get_account(validated_data['account_id'])
            instance.account = account
        instance.action = validated_data.get('action', instance.action)
        instance.save()
        return instance

    def validate_currency(self, value):
        cny = Currency.get_currency(currency=value.upper())
        if not cny:
            raise serializers.ValidationError(f"Currency does not exist {value}")
        return value

    @property
    def currency_mnemonic(self):
        return self.validated_data.get('currency', {}).get('mnemonic', None)

    @property
    def calendar(self):
        return self.validated_data.get('calendar', None)

    @property
    def periodicity(self):
        return self.validated_data.get('periodicity', None)

    @property
    def amount(self):
        return self.validated_data.get('amount', None)

    @property
    def name(self):
        return self.validated_data.get('name', None)

    @property
    def description(self):
        return self.validated_data.get('description', None)

    @property
    def date(self):
        return self.validated_data.get('date', None)

    @property
    def end_date(self):
        return self.validated_data.get('end_date', None)

    def calculate_is_forward(self, instance):
        return instance.draftfxforwardposition_set.count() > 0

    def update_is_forward(self, instance):
        instance.is_forward = self.calculate_is_forward(instance)

    def to_representation(self, instance):
        self.update_is_forward(instance)
        representation = super().to_representation(instance)
        # You can add more customization to the representation if needed
        return representation


class CashflowSerializer(serializers.ModelSerializer):
    """
    A serializer for the CashFlow model.
    """
    currency = CurrencySerializer()
    account = AccountSummarySerializer(required=True)

    # A cashflow can be associated with an installment.
    installment = InstallmentSerializer(required=False)

    calendar = serializers.ChoiceField(required=False,
                                       choices=[(cal.value, cal.name) for cal in CashFlow.CalendarType],
                                       default=CashFlow.CalendarType.NULL_CALENDAR.name)

    roll_convention = serializers.ChoiceField(required=False,
                                              choices=CashFlow.RollConvention.choices,
                                              default=CashFlow.RollConvention.UNADJUSTED.name)

    # A cashflow can be associated with a draft cashflow.
    draft = DraftCashflowSerializer(required=False)

    date = serializers.DateTimeField(required=True, default_timezone=pytz.UTC)

    created = serializers.DateTimeField(required=True, default_timezone=pytz.UTC)

    draft_fxforward = DraftFxForwardSerializer(many=True, read_only=True, source='draftfxforwardposition_set')

    fxforward = FxForwardSerializer(many=True, read_only=True, source='fxforwardposition_set')

    is_forward = serializers.BooleanField(default=False)

    booked_rate = serializers.FloatField(read_only=True)
    booked_base_amount = serializers.FloatField(read_only=True)
    booked_cntr_amount = serializers.FloatField(read_only=True)

    def calculate_is_forward(self, instance):
        return instance.draftfxforwardposition_set.count() > 0 or instance.fxforwardposition_set.count() > 0

    def update_is_forward(self, instance):
        instance.is_forward = self.calculate_is_forward(instance)

    def to_representation(self, instance):
        self.update_is_forward(instance)
        representation = super().to_representation(instance)
        # You can add more customization to the representation if needed
        return representation

    class Meta:
        model = CashFlow
        fields = ['id',
                  'date',
                  'end_date',
                  'next_date',
                  'currency',
                  'amount',
                  'created',
                  'modified',
                  'name',
                  'description',
                  'status',
                  'installment',
                  'account',
                  'periodicity',
                  'calendar',
                  'roll_convention',
                  'draft',
                  'draft_fxforward',
                  'fxforward',
                  'is_forward',
                  'indicative_rate',
                  'indicative_base_amount',
                  'indicative_cntr_amount',
                  'booked_rate',
                  'booked_base_amount',
                  'booked_cntr_amount'
                  ]


class CashflowNoteSerializer(serializers.ModelSerializer):
    """
    A serializer for the CashFlowNote model.
    """
    cashflow = serializers.PrimaryKeyRelatedField(source='cashflow_id', read_only=True)
    created = serializers.DateTimeField(required=False, read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(source='created_by_id', read_only=True)
    modified = serializers.DateTimeField(required=False, read_only=True)
    modified_by = serializers.PrimaryKeyRelatedField(source='created_by_id', read_only=True)

    class Meta:
        model = CashFlowNote
        fields = ['id', 'cashflow', 'description', 'created', 'created_by', 'modified', 'modified_by']


# This serializer is unfortunately different than the default CashFlowSerializer.
# todo(Ghais): Refactor this to be a single serializer.
class CashFlowCoreSerializer(serializers.Serializer):
    """
    This serializer is used to serialize incoming cashflow requests.
    """
    amount = serializers.FloatField()
    currency = serializers.CharField()
    pay_date = serializers.DateTimeField()
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    periodicity = serializers.CharField(required=False)
    calendar = serializers.ChoiceField(required=False,
                                       choices=[(cal.name, cal.name) for cal in CashFlow.CalendarType],
                                       default=CashFlow.CalendarType.NULL_CALENDAR.name)

    end_date = serializers.DateTimeField(required=False)
    roll_convention = serializers.ChoiceField(required=False,
                                              choices=CashFlow.RollConvention.choices,
                                              default=CashFlow.RollConvention.UNADJUSTED.name)

    draft = DraftCashflowSerializer(required=False)

    installment = serializers.IntegerField(required=False)

    fx_forward = FxForwardSerializer(required=False, many=True)

    draft_fx_forward = DraftFxForwardSerializer(required=False, many=True)

    def validate_currency(self, value):
        cny = Currency.get_currency(currency=value)
        if not cny:
            raise serializers.ValidationError(f"Currency does not exist {value}")
        return value

    def validate_amount(self, value):
        if value == 0:
            raise serializers.ValidationError(f"Cash flow amount cannot be zero")
        return value

    def get_calendar(self):
        cal_name = self.data.get('calendar')
        if cal_name:
            return CashFlow.CalendarType.from_name(cal_name)
        else:
            return None

    def get_roll_convention(self):
        roll_convention = self.data.get('roll_convention')
        if roll_convention:
            return CashFlow.RollConvention.from_name(roll_convention)
        else:
            return None


class CashFlowActionStatusSerializer(ActionStatusSerializer):
    ERROR_CODE_CHOICES = (
        ('missing_setup_intent', 'Missing setup intent'),
        ('missing_payment', 'Missing Payment'),
        ('charge_failed', 'Charge failed'),
        ('internal_server_error', 'Internal server error')
    )

    code = serializers.ChoiceField(choices=ERROR_CODE_CHOICES)
