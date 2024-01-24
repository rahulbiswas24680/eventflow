
from rest_framework import generics
from ..models import EventAnalytics, TicketTypeAnalytics
from .serializers import EventAnalyticsSerializer, TicketTypeAnalyticsSerializer


class EventAnalyticsDetailView(generics.RetrieveAPIView):
    queryset = EventAnalytics.objects.all()
    serializer_class = EventAnalyticsSerializer


class TicketTypeAnalyticsDetailView(generics.RetrieveAPIView):
    queryset = TicketTypeAnalytics.objects.all()
    serializer_class = TicketTypeAnalyticsSerializer
