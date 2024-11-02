from django.urls import path
from .views import events_home, event_detail


urlpatterns = [
    path("", events_home, name='events-home'),
    path("event/<int:event_id>", event_detail, name='event-detail'),
]