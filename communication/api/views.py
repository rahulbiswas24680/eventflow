
from rest_framework import generics

from ..models import Notification
from .serializers import NotificationSerializer


class NotificationListCreateView(generics.ListCreateAPIView):
    serializer_class = NotificationSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        qs = Notification.objects.filter(
            user=self.request.user).order_by('created_at')
        return qs

    def list(self, request, *args, **kwargs):
        # Send notification email when listing notifications
        return super().list(request, *args, **kwargs)


class NotificationDetailView(generics.RetrieveAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
