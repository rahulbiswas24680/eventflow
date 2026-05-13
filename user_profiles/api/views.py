from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import CustomUser, UserRSVPHistory, Organizer, Role
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
        # Return RSVP history entries belonging to the authenticated user
        return super().get_queryset().filter(user=self.request.user)


class UserRSVPHistoryDetailView(generics.RetrieveAPIView):
    queryset = UserRSVPHistory.objects.all()
    serializer_class = UserRSVPHistoryDetailsSerializer

    def get_queryset(self):
        # Ensure the user can only access their own RSVP history details
        return super().get_queryset().filter(user=self.request.user)


class OrganizersListCreateView(generics.ListCreateAPIView):
    queryset = Organizer.objects.all()
    serializer_class = OrganizerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Organizer.objects.filter(user=self.request.user)
        print(qs, self.request.user)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        return super().perform_create(serializer)


class OrganizerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for retrieving, updating, or deleting a single Organizer.
    Only the owner (creator) can modify or delete.
    """
    queryset = Organizer.objects.all()
    serializer_class = OrganizerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Restrict to organizers owned by the requesting user
        return super().get_queryset().filter(user=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def become_organizer(request):
    """
    API endpoint to add Organizer role to user's available_roles
    and create an Organizer profile if not exists.
    """
    user = request.user
    
    # Check if user already has organizer role
    try:
        organizer_role = Role.objects.get(name='organizer')
    except Role.DoesNotExist:
        return Response(
            {'error': 'Organizer role not found. Please contact admin.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Add organizer role if not already in available_roles
    if not user.available_roles.filter(id=organizer_role.id).exists():
        user.available_roles.add(organizer_role)
    
    # Create organizer profile if not exists
    organizer, created = Organizer.objects.get_or_create(
        user=user,
        defaults={
            'organizer_name': user.get_full_name() or user.username,
            'organizer_email': user.email,
            'created_by': user,
            'modified_by': user,
        }
    )
    
    # Set current_role to organizer if not set
    if not user.current_role or user.current_role.name == 'attendee':
        user.current_role = organizer_role
        user.save(update_fields=['current_role'])
    
    if created:
        return Response({
            'success': True,
            'message': 'Organizer profile created successfully!'
        }, status=status.HTTP_201_CREATED)
    else:
        return Response({
            'success': True,
            'message': 'You are now an organizer!'
        }, status=status.HTTP_200_OK)
