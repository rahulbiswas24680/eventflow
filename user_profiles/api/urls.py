from django.urls import path
from .views import (
    UserProfileDetailView,
    UserRSVPHistoryListCreateView,
    UserRSVPHistoryDetailView,
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
]
