from django.shortcuts import render


def rsvp_checkout(request, event_id, ticket_id):
    return render(request, "payments/rsvp_checkout.html")