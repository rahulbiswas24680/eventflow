from rest_framework import generics
from rest_framework import status
from ..models import RSVP, Event, TicketType
from .serializers import (
    EventSerializer,
    RSVPSerializer,
    TicketTypeSerializer,
    EventDetailSerializer,
)
from drf_spectacular.utils import extend_schema


class EventListCreateView(generics.ListCreateAPIView):
    queryset = Event.objects.all().order_by("created_at")
    serializer_class = EventSerializer


class EventDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Event.objects.all()
    serializer_class = EventDetailSerializer


class TicketTypeListCreateView(generics.ListCreateAPIView):
    queryset = TicketType.objects.all().order_by("created_at")
    serializer_class = TicketTypeSerializer


class TicketTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TicketType.objects.all()
    serializer_class = TicketTypeSerializer


@extend_schema(
    summary="List all the users of each event.",
    description="Return a list of all user details of each event.",
)
class RSVPListCreateView(generics.ListCreateAPIView):
    queryset = RSVP.objects.all().order_by("created_at")
    serializer_class = RSVPSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        event_id = self.request.query_params.get("event")
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        return queryset


class RSVPDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = RSVP.objects.all()
    serializer_class = RSVPSerializer
