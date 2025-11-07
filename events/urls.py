from django.urls import path
from .views import events_home, event_detail, create_event, OrganizerListView, OrganizerCreateView, OrganizerUpdateView, OrganizerDeleteView
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path("", events_home, name='events-home'),
    path("event/<int:event_id>", event_detail, name='event-detail'),
    path("events/create/", create_event, name="create-event"),

    # organizers page
    path("organizers/list/", OrganizerListView.as_view(), name='organizers-list'),
    path("organizers/create/", OrganizerCreateView.as_view(), name='organizer-create'),
    path("organizers/edit/<int:pk>/", OrganizerUpdateView.as_view(), name="organizer-edit"),
    path("organizers/delete/<int:pk>/", OrganizerDeleteView.as_view(), name="organizer-delete"),

    # ------------------------------------------------------------------
    # Front‑end pages that consume the new user‑profile / RSVP‑history APIs
    # ------------------------------------------------------------------
    path(
        "profile/",
        login_required(TemplateView.as_view(template_name="events/profile.html")),
        name="user-profile",
    ),
    path(
        "my-rsvp/",
        login_required(TemplateView.as_view(template_name="events/my_rsvp.html")),
        name="my-rsvp-history",
    ),
]
