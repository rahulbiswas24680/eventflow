import json

import stripe
from decouple import config
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.shortcuts import HttpResponse, redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework import filters, generics, permissions, status
from rest_framework.exceptions import NotAcceptable, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from choices import PAYMENT_STATUS_CHOICES
from events.models import RSVP, Event, TicketType
from qr_codes.models import QRCode

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

        except stripe.error.StripeError:
            return Response(
                {"error": "Something went wrong in payment session"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"checkout_url": checkout_session.url})


@csrf_exempt
def stripe_webhook(request):
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

    # ✅ Handle successful payment
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session.get("id")

        user_id = session.get("client_reference_id") or session["metadata"].get("user_id")

        try:
            user = get_user_model().objects.get(id=user_id)
        except Exception:
            return HttpResponse(status=400)

        # 🔑 Get all transactions belonging to this session
        transactions = Transaction.objects.filter(session_id=session_id)

        if transactions.exists():
            for txn in transactions:
                txn.payment_status = "SUCCESS"
                txn.transaction_id = session.get("payment_intent")
                

                ticket_obj = txn.ticket_type

                # RSVP create per ticket
                rsvp_obj = rsvp_create(
                    ticket_obj,
                    user,
                    txn.transaction_id,
                    session.get("metadata", {}),
                    txn.quantity,
                    txn.amount
                )

                # Link transaction with the rsvp
                txn.rsvp = rsvp_obj
                txn.save()
                # Generate QR linked to transaction + RSVP
                qr = link_with_qrcode(txn, rsvp_obj)

                # Send confirmation email (1 email per ticket)
                email = EmailMessage(
                    "Your Ticket Confirmation",
                    f"Thanks for purchasing {ticket_obj.name}! Please find your QR code attached.",
                    to=[txn.user.email],
                )
                email.attach_file(qr.code_image.path)
                email.send()

    return HttpResponse(status=200)



def rsvp_create(ticket_obj, user, transaction_id, metadata, ticket_qty, amount):
    return RSVP.objects.create(
        event=ticket_obj.event,
        attendee=user,
        transaction_id=transaction_id,
        ticket_qty=ticket_qty,
        total_charge=amount * ticket_qty,
        is_active=True,
        metadata=metadata
    )


def transaction_create(checkout_session, ticket_obj, rsvp_obj, quantity):
    transaction_obj = Transaction.objects.create(
        user=rsvp_obj.attendee,
        rsvp=rsvp_obj,
        ticket_type=ticket_obj.ticket_type,
        currency=ticket_obj.currency,
        amount=ticket_obj.amount,
        quantity=quantity,
        transaction_id=checkout_session.id,
        payment_status=PAYMENT_STATUS_CHOICES[0][0],
    )
    return transaction_obj


def link_with_qrcode(transaction_obj, rsvp):
#     code_data = f"""//////
# {transaction_obj.ticket_type.name}-
# {transaction_obj.currency}-
# {transaction_obj.amount}-
# {transaction_obj.quantity}-
# {transaction_obj.payment_status}-
# {rsvp.id}-
# {transaction_obj.transaction_id}
# //////
# """
    qr_obj = QRCode.objects.create(
        transaction=transaction_obj
    )
    return qr_obj


# class PaymentAPI(APIView):
#     serializer_class = CardInformationSerializer

#     def post(self, request):
#         serializer = self.serializer_class(data=request.data)
#         response = {}

#         if serializer.is_valid():
#             data_dict = serializer.validated_data  # Use validated_data instead of data
#             stripe.api_key = 'your-key-goes-here'
#             response = self.stripe_card_payment(data_dict=data_dict)
#         else:
#             response = {'errors': serializer.errors,
#                         'status': status.HTTP_400_BAD_REQUEST}

#         return Response(response)

#     def stripe_card_payment(self, data_dict):
#         try:
#             card_details = {
#                 "number": data_dict['card_number'],
#                 "exp_month": data_dict['expiry_month'],
#                 "exp_year": data_dict['expiry_year'],
#                 "cvc": data_dict['cvc']
#             }

#             payment_intent = stripe.PaymentIntent.create(
#                 amount=10000,  # You can adjust the amount as needed
#                 currency='inr'
#             )

#             payment_intent_modified = stripe.PaymentIntent.modify(
#                 payment_intent['id'],
#                 payment_method=card_details,
#             )

#             try:
#                 payment_confirm = stripe.PaymentIntent.confirm(
#                     payment_intent['id']
#                 )
#                 payment_intent_modified = stripe.PaymentIntent.retrieve(
#                     payment_intent['id'])
#             except stripe.error.CardError as e:
#                 error = e.error
#                 payment_confirm = {
#                     "stripe_payment_error": "Failed",
#                     "code": error.code,
#                     "message": error.message,
#                     'status': "Failed"
#                 }

#             if payment_intent_modified and payment_intent_modified['status'] == 'succeeded':
#                 response = {
#                     'message': "Card Payment Success",
#                     'status': status.HTTP_200_OK,
#                     "card_details": card_details,
#                     "payment_intent": payment_intent_modified,
#                     "payment_confirm": payment_confirm
#                 }
#             else:
#                 response = {
#                     'message': "Card Payment Failed",
#                     'status': status.HTTP_400_BAD_REQUEST,
#                     "card_details": card_details,
#                     "payment_intent": payment_intent_modified,
#                     "payment_confirm": payment_confirm
#                 }

#         except stripe.error.CardError as e:
#             error = e.error
#             response = {
#                 'error': f"Card Payment Failed - {error.message}",
#                 'status': status.HTTP_400_BAD_REQUEST,
#                 "payment_intent": {"id": "Null"},
#                 "payment_confirm": {'status': "Failed"}
#             }

#         return response


def transaction_qr(request):
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
