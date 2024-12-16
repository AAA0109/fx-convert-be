from rest_framework import serializers

from main.apps.corpay.api.serializers.spot.book_deal import BookDealRequestSerializer
from main.apps.corpay.api.serializers.spot.instruct_deal import InstructDealRequestSerializer


class BookInstructDealRequestSerializer(serializers.Serializer):
    book_request = BookDealRequestSerializer()
    instruct_request = InstructDealRequestSerializer()

class SaveInstructRequestSerializer(serializers.Serializer):
    quote_id = serializers.IntegerField(required=False)
    instruct_request = InstructDealRequestSerializer()
