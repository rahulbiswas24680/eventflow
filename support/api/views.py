
from rest_framework import generics
from ..models import SupportTicket
from .serializers import SupportTicketSerializer


class SupportTicketListCreateView(generics.ListCreateAPIView):
    queryset = SupportTicket.objects.all()
    serializer_class = SupportTicketSerializer


class SupportTicketDetailView(generics.RetrieveAPIView):
    queryset = SupportTicket.objects.all()
    serializer_class = SupportTicketSerializer
