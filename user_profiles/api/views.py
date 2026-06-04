from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import CustomUser, Organizer, Role
from .serializers import (
    UserProfileSerializer,
    OrganizerSerializer
)


class UserProfileDetailView(generics.RetrieveAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserProfileSerializer

    # def get_serializer_context(self):
    #     context = super().get_serializer_context()
    #     context.update({"user": self.request.user})
    #     return context


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

    try:
        organizer_role = Role.objects.get(name='organizer')
    except Role.DoesNotExist:
        return Response(
            {'error': 'Organizer role not found. Please contact admin.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    has_role = user.available_roles.filter(id=organizer_role.id).exists()
    existing_profile = Organizer.objects.filter(user=user).first()

    if has_role and existing_profile:
        return Response({
            'success': True,
            'message': 'You are already an organizer!',
        }, status=status.HTTP_200_OK)

    if not has_role:
        user.available_roles.add(organizer_role)

    if not existing_profile:
        Organizer.objects.create(
            user=user,
            organizer_name=user.get_full_name() or user.username,
            organizer_email=user.email,
            created_by=user,
            modified_by=user,
        )
    elif Organizer.objects.filter(user=user).count() > 1:
        orgs = Organizer.objects.filter(user=user).order_by('id')
        for org in orgs[1:]:
            org.delete()

    if not user.current_role or user.current_role.name == 'attendee':
        user.current_role = organizer_role
        user.save(update_fields=['current_role'])

    return Response({
        'success': True,
        'message': 'You are now an organizer!',
    }, status=status.HTTP_200_OK)
