from forex_python.converter import CurrencyRates
from rest_framework import serializers
from typing import List
from ..models import RSVP, Event, TicketType, EventImage
from qr_codes.models import QRCode
from payments.models import Transaction


class EventImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventImage
        fields = ("image",)


class EventSerializer(serializers.ModelSerializer):
    images = EventImageSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = "__all__"
    
    def to_representation(self, obj):
        representation = super().to_representation(obj)
        representation['organizer'] = obj.organizer.organizer_name
        return representation


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
    if currency == "INR":
        return amount
    
    from django.core.cache import cache
    
    cache_key = f"forex_rate:{currency}:INR"
    conversion_rate = cache.get(cache_key)
    
    if conversion_rate is None:
        c = CurrencyRates()
        conversion_rate = c.get_rate(currency, "INR")
        cache.set(cache_key, conversion_rate, timeout=86400)
    
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
    event_name = serializers.CharField(source='event.name', read_only=True)
    attendee_name = serializers.CharField(source='attendee.username', read_only=True)
    attendee_email = serializers.CharField(source='attendee.email', read_only=True)
    ticket_qr = serializers.SerializerMethodField(read_only=True)
    ticket_type = serializers.SerializerMethodField(read_only=True)
    status = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = RSVP
        fields = "__all__"
        read_only_fields = ('event_name', 'attendee_name', 'attendee_email', 'ticket_qr', 'ticket_type')

    def get_ticket_qr(self, obj):
        try:
            qr_obj = QRCode.objects.get(transaction__transaction_id=obj.transaction_id)
            if qr_obj.code_image:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(qr_obj.code_image.url)
                return qr_obj.code_image.url
        except QRCode.DoesNotExist:
            return None

    def get_ticket_type(self, obj):
        # ticket_price = obj.total_charge // obj.ticket_qty
        # ticket = obj.event.tickettype_set.filter(price=ticket_price)
        # print(ticket)
        # return ticket[0].name if ticket else None
        try:
            return obj.transaction.ticket_type.name
        except Transaction.DoesNotExist:
            return None
        
    def get_status(self, obj):
        if obj.is_attended:
            status = "attended"
        elif not obj.is_attended:
            status = "registered"
        elif obj.is_cancelled:
            status = "cancelled"
        return status