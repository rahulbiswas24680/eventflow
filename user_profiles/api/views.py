from rest_framework import generics

from ..models import UserProfile, UserRSVPHistory
from .serializers import UserProfileSerializer, UserRSVPHistorySerializer


class UserProfileDetailView(generics.RetrieveAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer


class UserRSVPHistoryListCreateView(generics.ListCreateAPIView):
    queryset = UserRSVPHistory.objects.all()
    serializer_class = UserRSVPHistorySerializer


class UserRSVPHistoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserRSVPHistory.objects.all()
    serializer_class = UserRSVPHistorySerializer
