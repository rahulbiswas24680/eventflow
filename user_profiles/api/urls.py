from django.urls import path
from .views import (
    UserProfileDetailView,
    UserRSVPHistoryListCreateView,
    UserRSVPHistoryDetailView,

    OrganizersListCreateView,
    OrganizerDetailView,
)

urlpatterns = [
    # UserProfileDetailView
    path(
        "profiles/<int:pk>/",
        UserProfileDetailView.as_view(),
        name="user-profile-detail",
    ),


    # UserRSVPHistory
    path(
        "rsvp-history/",
        UserRSVPHistoryListCreateView.as_view(),
        name="rsvp-history-list",
    ),
    path(
        "rsvp-history/<int:pk>/",
        UserRSVPHistoryDetailView.as_view(),
        name="user-rsvp-history-detail",
    ),


    path("organizers/", OrganizersListCreateView.as_view(), name="organizers-list"),
    path("organizers/<int:pk>/", OrganizerDetailView.as_view(), name="organizer-detail"),
]
