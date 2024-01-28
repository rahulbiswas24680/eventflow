from forex_python.converter import CurrencyRates
from rest_framework import serializers
from typing import List
from ..models import RSVP, Event, TicketType, EventImage


class EventImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventImage
        fields = ("image",)


class EventSerializer(serializers.ModelSerializer):
    images = EventImageSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = "__all__"


class EventDetailSerializer(serializers.ModelSerializer):
    images = EventImageSerializer(many=True, read_only=True)
    tickets_details = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Event
        fields = "__all__"

    def get_tickets_details(self, obj) -> List[dict]:
        qs = TicketType.objects.filter(event=obj).order_by("price")
        serialized = TicketTypeSerializer(qs, many=True)
        return serialized.data


class CurrencyAwareDecimalField(serializers.DecimalField):
    """
    Custom serializer field for handling currency conversion.
    """

    def __init__(self, *args, **kwargs):
        self.currency_field = kwargs.pop("currency_field", None)
        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        # When serializing, return the original value
        return super().to_representation(value)

    def to_internal_value(self, data):
        # When deserializing, convert the value based on the provided currency
        if self.currency_field:
            currency = self.currency_field
            # Your currency conversion logic goes here
            converted_value = convert_to_base_currency(data, currency)
            return converted_value

        # If no currency is provided, return the original value
        return super().to_internal_value(data)


def convert_to_base_currency(amount, currency):
    # Use an external service or library to perform currency conversion
    # In this example, we use the forex-python library
    c = CurrencyRates()
    # Convert to INR as an example
    conversion_rate = c.get_rate(currency, "INR")
    converted_amount = amount * conversion_rate
    return converted_amount


class TicketTypeSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(use_url=True, read_only=True)
    # price = CurrencyAwareDecimalField(
    #     max_digits=10, decimal_places=2,
    #     currency_field='currency', write_only=True)

    class Meta:
        model = TicketType
        # fields = "__all__"
        exclude = ["created_at", "stripe_price_id"]


class RSVPSerializer(serializers.ModelSerializer):
    class Meta:
        model = RSVP
        fields = "__all__"
