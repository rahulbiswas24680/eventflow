
from rest_framework import generics

from ..models import RSVP, Event, TicketType
from .serializers import EventSerializer, RSVPSerializer, TicketTypeSerializer


class EventListCreateView(generics.ListCreateAPIView):
    queryset = Event.objects.all().order_by('created_at')
    serializer_class = EventSerializer


class EventDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer


class TicketTypeListCreateView(generics.ListCreateAPIView):
    queryset = TicketType.objects.all().order_by('created_at')
    serializer_class = TicketTypeSerializer


class TicketTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TicketType.objects.all()
    serializer_class = TicketTypeSerializer


class RSVPListCreateView(generics.ListCreateAPIView):
    queryset = RSVP.objects.all().order_by('created_at')
    serializer_class = RSVPSerializer


class RSVPDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = RSVP.objects.all()
    serializer_class = RSVPSerializer
