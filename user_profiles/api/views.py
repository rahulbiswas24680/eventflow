from rest_framework import generics

from ..models import CustomUser, UserRSVPHistory, Organizer
from .serializers import (
    UserProfileSerializer,
    UserRSVPHistorySerializer,
    UserRSVPHistoryDetailsSerializer,
    OrganizerSerializer
)


class UserProfileDetailView(generics.RetrieveAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserProfileSerializer

    # def get_serializer_context(self):
    #     context = super().get_serializer_context()
    #     context.update({"user": self.request.user})
    #     return context


class UserRSVPHistoryListCreateView(generics.ListCreateAPIView):
    queryset = UserRSVPHistory.objects.all()
    serializer_class = UserRSVPHistorySerializer

    def get_queryset(self):
        return (
            super().get_queryset().filter(user_profile__user=self.request.user)
        )


class UserRSVPHistoryDetailView(generics.RetrieveAPIView):
    queryset = UserRSVPHistory.objects.all()
    serializer_class = UserRSVPHistoryDetailsSerializer

    def get_queryset(self):
        return (
            super().get_queryset().filter(user_profile__user=self.request.user)
        )


class OrganizersListCreateView(generics.ListCreateAPIView):
    queryset = Organizer.objects.all()
    serializer_class = OrganizerSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        return super().perform_create(serializer)
    
