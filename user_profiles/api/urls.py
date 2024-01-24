from django.urls import path
from .views import UserProfileDetailView, UserRSVPHistoryListCreateView

urlpatterns = [
    # UserProfileDetailView
    path('profiles/<int:pk>/', UserProfileDetailView.as_view(), name='user-profile-detail'),

    # UserRSVPHistoryListCreateView
    path('rsvp-history/', UserRSVPHistoryListCreateView.as_view(), name='rsvp-history-list'),
]
