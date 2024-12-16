from rest_framework import serializers
from main.apps.account.models.user import User

from main.apps.currency.models.currency import Currency
from main.apps.oems.api.serializers.fields import CurrencyAmountField
from main.apps.payment.models.payment import Payment


class ApproverRequestSerializer(serializers.Serializer):
    lock_side_currency = serializers.SlugRelatedField(slug_field='mnemonic',
                                            queryset=Currency.objects.all())
    lock_side_amount = CurrencyAmountField(coerce_to_string=False)
    value_date = serializers.DateField()


class ApproverSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email',]


class ApproverResponseSerializer(serializers.Serializer):
    approvers = ApproverSerializer(many=True)


class RequestApprovalSerializer(serializers.Serializer):
    payment_id = serializers.SlugRelatedField(slug_field='id', queryset=Payment.objects.all())
    approver_user_ids = serializers.ListField(child=serializers.IntegerField())

    def validate(self, attrs):
        attrs = super().validate(attrs)
        n_ids = len(attrs['approver_user_ids'])
        if n_ids == 0:
            raise serializers.ValidationError(f"At least an approver's user id required")
        elif n_ids > 2:
            raise serializers.ValidationError(f"Maximum of 2 approvers allowed")
        return attrs

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        users = User.objects.filter(id__in=data['approver_user_ids'])
        data['approver_user_ids'] = list(users)
        return data


class ApproveRequestSerializer(serializers.Serializer):
    payment_id = serializers.SlugRelatedField(slug_field='id', queryset=Payment.objects.all())
