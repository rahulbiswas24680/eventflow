from django.urls import path
from .views import rsvp_checkout


urlpatterns = [
    path("<int:event_id>/<int:ticket_id>/", rsvp_checkout, name='rsvp-checkout'),
]