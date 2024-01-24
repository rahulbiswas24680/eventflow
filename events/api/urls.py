from django.urls import path

from .views import (EventDetailView, EventListCreateView, RSVPDetailView,
                    RSVPListCreateView, TicketTypeDetailView,
                    TicketTypeListCreateView)

urlpatterns = [
    path('list/', EventListCreateView.as_view(), name='event-list'),
    path('detail/<int:pk>/', EventDetailView.as_view(), name='event-detail'),
    
    path('tickettypes/', TicketTypeListCreateView.as_view(), name='tickettype-list'),
    path('tickettypes/<int:pk>/', TicketTypeDetailView.as_view(), name='tickettype-detail'),
    
    path('rsvps/', RSVPListCreateView.as_view(), name='rsvp-list'),
    path('rsvps/<int:pk>/', RSVPDetailView.as_view(), name='rsvp-detail'),
]
