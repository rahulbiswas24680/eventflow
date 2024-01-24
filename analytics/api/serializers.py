

from rest_framework import serializers
from ..models import EventAnalytics, TicketTypeAnalytics

class EventAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventAnalytics
        fields = '__all__'

class TicketTypeAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketTypeAnalytics
        fields = '__all__'
