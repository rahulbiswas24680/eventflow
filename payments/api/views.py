import stripe
from decouple import config
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import HttpResponse, redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework import filters, generics, permissions, status
from rest_framework.exceptions import NotAcceptable, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from events.models import Event, TicketType

from ..models import Transaction, TransactionOfOrganizer
from .serializers import (
    TransactionOfOrganizerSerializer,
    TransactionSerializer)

stripe.api_key = config("STRIPE_SECRET_KEY")


# class EventPaymentBillListView(generics.ListAPIView):
#     queryset = EventPaymentBill.objects.all()
#     serializer_class = EventPaymentBillSerializer


# class EventPaymentBillDetailView(generics.RetrieveAPIView):
#     queryset = EventPaymentBill.objects.all()
#     serializer_class = EventPaymentBillSerializer



class EventsCheckoutAPIView(APIView):

    def get(self, request, *args, **kwargs):
        cart_items = request.session.get("cart", [])  # stored as [{id, quantity}, ...]
        if not cart_items:
            return Response({"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)
        print(cart_items)
        event = None
        tickets_data = []
        total_cost = 0

        for item in cart_items:
            try:
                ticket = TicketType.objects.get(id=item["id"])
                if not event:
                    event = ticket.event
                qty = int(item.get("quantity", 1))
                subtotal = ticket.price * qty

                tickets_data.append({
                    "id": ticket.id,
                    "name": ticket.name,
                    "price": ticket.price,
                    "quantity": qty,
                    "subtotal": subtotal,
                })

                total_cost += subtotal
            except TicketType.DoesNotExist:
                continue

        if not event:
            return Response({"error": "Invalid cart data"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "event": {
                "id": event.id,
                "name": event.name,
                "date": event.date,
                "location": event.location,
            },
            "tickets": tickets_data,
            "total_cost": total_cost
        }, status=status.HTTP_200_OK)


class TransactionListCreateView(generics.ListCreateAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer


class TransactionDetailView(generics.RetrieveAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer


class TransactionOfOrganizerListCreateView(generics.ListCreateAPIView):
    queryset = TransactionOfOrganizer.objects.all()
    serializer_class = TransactionOfOrganizerSerializer


class TransactionOfOrganizerDetailView(generics.RetrieveAPIView):
    queryset = TransactionOfOrganizer.objects.all()
    serializer_class = TransactionOfOrganizerSerializer


class TicketCheckoutApiView(APIView):
    """
    To buy multiple tickets:

    [
        { "ticket_id": 4, "quantity": 2 },
        { "ticket_id": 7, "quantity": 1 },
        { "ticket_id": 8, "quantity": 3 }
    ]
    """

    serializer_class = None

    def post(self, request, *args, **kwargs):
        tickets_data = request.data['tickets']  # expecting a list
        # if not isinstance(tickets_data, list) or not tickets_data:
        #     raise NotAcceptable("Request must be a non-empty list of tickets.")

        line_items = []
        transactions_to_create = []

        try:
            for item in tickets_data:
                ticket_id = item.get("ticket_id")
                quantity = item.get("quantity")

                if not (ticket_id and quantity):
                    raise NotAcceptable("Each ticket must have ticket_id and quantity.")

                try:
                    ticket_obj = TicketType.objects.get(id=ticket_id)
                except TicketType.DoesNotExist:
                    raise NotFound(f"Ticket with id {ticket_id} not found.")

                if not ticket_obj.stripe_price_id:
                    return Response(
                        {"error": f"Stripe price ID missing for ticket {ticket_id}."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

                # Build Stripe line item
                line_items.append(
                    {
                        "price": ticket_obj.stripe_price_id,
                        "quantity": quantity,
                    }
                )

                # Prepare transaction entry
                transactions_to_create.append(
                    Transaction(
                        user=request.user,
                        ticket_type=ticket_obj,
                        currency="INR",
                        amount=ticket_obj.price,
                        quantity=quantity,
                        payment_status="PENDING",
                    )
                )

            # Create Stripe checkout session
            checkout_session = stripe.checkout.Session.create(
                line_items=line_items,
                payment_method_types=["card"],
                mode="payment",
                success_url=settings.SITE_URL
                + "/checkout/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=settings.SITE_URL + "/checkout/cancel",
                client_reference_id=str(request.user.id),
                metadata={"user_id": request.user.id},
            )
            print('checkout session url', settings.SITE_URL)
            # Add Stripe session_id to each transaction and bulk create
            for txn in transactions_to_create:
                txn.session_id = checkout_session["id"]
            Transaction.objects.bulk_create(transactions_to_create)

        except stripe.error.StripeError as e:
            print('stripe session error == ', e)
            return Response(
                {"error": "Something went wrong in payment session"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"checkout_url": checkout_session.url})


@csrf_exempt
def stripe_webhook(request):
    """
    Stripe webhook handler - now delegates to Celery task for async processing.
    
    Instead of processing everything synchronously (which blocks and can timeout),
    we queue the task and return immediately. This ensures:
    - Fast webhook response (< 50ms vs ~2s)
    - Stripe doesn't retry due to timeout
    - Background processing handles QR, RSVP, email
    """
    from ..tasks import process_checkout_session
    
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET_KEY
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session.get("id")
        payment_intent = session.get("payment_intent")

        user_id = session.get("client_reference_id") or session["metadata"].get("user_id")

        if not user_id:
            return HttpResponse(status=400)
        
        try:
            get_user_model().objects.get(id=user_id)
        except Exception:
            return HttpResponse(status=400)
        
        # Update transaction with payment_intent from Stripe
        if payment_intent:
            Transaction.objects.filter(session_id=session_id).update(
                transaction_id=payment_intent
            )
        
        process_checkout_session.delay(session_id)

    return HttpResponse(status=200)


def transaction_qr(request):
    """
    API endpoint to get QR code URL for a transaction by session_id.
    """
    from qr_codes.models import QRCode
    
    session_id = request.GET.get("session_id")
    if not session_id:
        return JsonResponse({"error": "session_id required"}, status=400)

    transaction = Transaction.objects.filter(session_id=session_id).first()
    if not transaction:
        return JsonResponse({"error": "transaction not found"}, status=404)

    qr = QRCode.objects.filter(transaction=transaction).first()
    if qr and qr.code_image:
        return JsonResponse({"qr_url": qr.code_image.url})
    return JsonResponse({"qr_url": None})
