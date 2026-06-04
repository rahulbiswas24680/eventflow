from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.generic import TemplateView
from .views import (OrganizerCreateView, OrganizerDeleteView,
                    OrganizerListView, OrganizerUpdateView, about_page,
                    all_events, create_event, dashboard, event_detail,
                    events_home, our_events, pricing_page, switch_role,
                    ticket_preview, dashboard_chart_data, update_event,
                    manage_attendees, user_profile)

urlpatterns = [

    # common urls
    path("dashboard/", dashboard, name='dashboard'),
    path("dashboard/chart-data/", dashboard_chart_data, name='dashboard-chart-data'),
    path(
        "profile/",
        user_profile,
        name="user-profile",
    ),
    path('switch-role/', switch_role, name='switch-role'),
    path("about/", about_page, name='about-page'),
    path("pricing/", pricing_page, name='pricing-page'),
]

attendee_urls = [
    path("", events_home, name='events-home'),
    path("events/", all_events, name='events-list'),
    path("event/<int:event_id>", event_detail, name='event-detail'),
    path(
        "my-rsvp/",
        login_required(TemplateView.as_view(template_name="events/my_rsvp.html")),
        name="my-rsvp-history",
    ),
    path("ticket/<str:rsvp_id>/", ticket_preview, name='preview-ticket'),
]

organizer_urls = [

    path("events/create/", create_event, name="create-event"),
    path("our-events/", our_events, name='our-events'),
    path("events/edit/<int:pk>/", update_event, name="update-event"),
    path("events/<int:event_id>/attendees/", manage_attendees, name="event-attendees"),

    # organizers page
    path("organizers/list/", OrganizerListView.as_view(), name='organizers-list'),
    path("organizers/create/", OrganizerCreateView.as_view(), name='organizer-create'),
    path("organizers/edit/<int:pk>/", OrganizerUpdateView.as_view(), name="organizer-edit"),
    path("organizers/delete/<int:pk>/", OrganizerDeleteView.as_view(), name="organizer-delete"),
]

urlpatterns += attendee_urls
urlpatterns += organizer_urls