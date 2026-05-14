from django.urls import path
from .views import (
    UserProfileDetailView,

    OrganizersListCreateView,
    OrganizerDetailView,
    become_organizer,
)

urlpatterns = [
    # UserProfileDetailView
    path(
        "profiles/<int:pk>/",
        UserProfileDetailView.as_view(),
        name="user-profile-detail",
    ),

    path("organizers/", OrganizersListCreateView.as_view(), name="organizers-list"),
    path("organizers/<int:pk>/", OrganizerDetailView.as_view(), name="organizer-detail"),
    path("become-organizer/", become_organizer, name="become-organizer-api"),
]
