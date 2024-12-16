from rest_framework import serializers

from main.apps.corpay.api.serializers.choices import PICKLIST_TYPES


class OnboardingPickListRequestSerializer(serializers.Serializer):
    pick_list_type = serializers.ChoiceField(choices=PICKLIST_TYPES)


class OnboardingPickListItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    string_value = serializers.CharField(source="stringValue")


class OnboardingPickListResponseSerializer(serializers.Serializer):
    annual_volume_range_list = OnboardingPickListItemSerializer(many=True, required=False,
                                                                source="annualVolumeRangeList")
    applicant_type_list = OnboardingPickListItemSerializer(many=True, required=False, source="applicantTypeList")
    business_type_list = OnboardingPickListItemSerializer(many=True, required=False, source="businessTypeList")
    purpose_of_transaction_list = OnboardingPickListItemSerializer(many=True, required=False,
                                                                   source="purposeOfTransactionList")
    trade_volume_range_list = OnboardingPickListItemSerializer(many=True, required=False,
                                                               source="tradeVolumeRangeList")
    nature_of_business_list = OnboardingPickListItemSerializer(many=True, required=False,
                                                               source="natureOfBusinessList")
