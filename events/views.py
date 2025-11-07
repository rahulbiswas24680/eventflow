from django.shortcuts import render, redirect
from .models import Event, TicketType
from .api.serializers import EventSerializer, EventDetailSerializer
from user_profiles.models import Organizer
from django.contrib import messages


def events_home(request):
    events = Event.objects.all()
    serializer = EventSerializer(events, many=True)
    context = {"events": serializer.data}
    return render(request, "events/events_home.html", context)


def event_detail(request, event_id):
    event = Event.objects.get(id=event_id)

    tickets = TicketType.objects.filter(event__id=event_id)
    print(tickets)
    context = {"event": event, "tickets": tickets}
    return render(request, "events/event_detail.html", context)


def organizers_masters(request):
    if request.method == "POST":
        print(request.POST)
        data = request.POST
        if data.get("privacy") and data.get("terms"):
            organizer = Organizer.objects.create(
                user=request.user,
                organizer_name=data.get("organizer_name"),
                organizer_slug=data.get("organizer_slug"),
                created_by=request.user,
                modified_by=request.user
            )
            messages.success(request, "Organizers has been added.")
            return redirect("organizers-masters")

        return redirect("organizers-masters")
    organizers = Organizer.objects.filter(user=request.user, is_active=True)
    return render(
        request,
        "events/organizers_masters.html",
        context={"organizers": organizers},
    )
