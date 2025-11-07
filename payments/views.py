import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from events.models import Event, TicketType

@login_required
def add_to_cart(request):
    if request.method == "POST":
        ticket_id = request.POST.get("ticket_id")
        qty = int(request.POST.get("quantity", 1))

        cart = request.session.get("cart", [])
        # check if ticket already in cart
        for item in cart:
            if item["id"] == int(ticket_id):
                item["quantity"] += qty
                break
        else:
            cart.append({"id": int(ticket_id), "quantity": qty})

        request.session["cart"] = cart
        request.session.modified = True

        return JsonResponse({"success": True, "cart": cart})
    
@login_required
def reset_cart(request):
    if request.method == "POST":
        # Get the old cart before clearing
        old_cart = request.session.get("cart", [])

        # Reset the cart
        request.session["cart"] = []
        request.session.modified = True

        return JsonResponse({
            "success": True,
            "old_cart": old_cart,   # just for debugging/confirmation
            "new_cart": []          # always empty after reset
        })
    
    return JsonResponse({"error": "Invalid request"}, status=400)

@login_required
def rsvp_checkout(request):
    # event = Event.objects.get(id=event_id)
    
    # cart_items = []
    # total_cost = 0

    # if request.method == "POST":
    #     try:
    #         cart_items = json.loads(request.body)  # [{id, name, price, quantity}, ...]
    #     except Exception as e:
    #         return JsonResponse({"error": "Invalid cart data"}, status=400)

    #     # calculate cost
    #     for item in cart_items:
    #         try:
    #             ticket = TicketType.objects.get(id=item["id"])
    #             qty = int(item.get("quantity", 1))
    #             total_cost += ticket.price * qty
    #             item["price"] = ticket.price  # overwrite to prevent tampering
    #         except TicketType.DoesNotExist:
    #             continue
    
    return render(request, "payments/rsvp_checkout.html", {
        # "event": event,
        # "tickets": cart_items,
        # "total_cost": total_cost,
    })

@login_required
def checkout_success(request):
    session_id = request.GET.get("session_id")  # comes from Stripe redirect
    context = {"session_id": session_id}
    return render(request, "payments/checkout_success.html", context)


@login_required
def checkout_cancel(request):
    return render(request, "payments/checkout_cancel.html")
