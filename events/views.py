from django.shortcuts import render
from .models import Event
from .api.serializers import EventSerializer, EventDetailSerializer



def events_home(request):
    events = Event.objects.all()
    serializer = EventSerializer(events, many=True)
    context = {
        'events': serializer.data
    }
    return render(request, "events/events_home.html", context)

def event_detail(request, event_id):
    events = Event.objects.get(id=event_id)
    serializer = EventDetailSerializer(events)
    context = {
        'event': serializer.data
    }
    return render(request, "events/event_detail.html", context)