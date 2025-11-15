from django.urls import path

from .views import (EventDetailView, EventListCreateView, RSVPDetailView,
                    RSVPListCreateView, TicketTypeDetailView,
                    TicketTypeListCreateView, delete_event_image,
                    delete_ticket_image, update_rsvp_status)

urlpatterns = [
    path('list/', EventListCreateView.as_view(), name='event-list'),
    path('detail/<int:pk>/', EventDetailView.as_view(), name='event-detail'),
    
    path('tickettypes/', TicketTypeListCreateView.as_view(), name='tickettype-list'),
    path('tickettypes/<int:pk>/', TicketTypeDetailView.as_view(), name='tickettype-detail'),
    
    path('rsvps/', RSVPListCreateView.as_view(), name='rsvp-list'),
    path('rsvps/<int:pk>/', RSVPDetailView.as_view(), name='rsvp-detail'),
    path('rsvp/<int:rsvp_id>/update/', update_rsvp_status, name='update_rsvp_status'),

    path("<int:event_id>/<int:image_id>/", delete_event_image, name="delete-event-image"),
    path("<int:event_id>/ticket-image/<int:ticket_id>/", delete_ticket_image, name="delete-ticket-image"),
]
