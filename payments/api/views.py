import stripe
from decouple import config
from django.conf import settings
from django.shortcuts import redirect
from rest_framework import filters, generics, permissions, status
from rest_framework.exceptions import NotFound, NotAcceptable
from rest_framework.response import Response
from rest_framework.views import APIView
from choices import (
    PAYMENT_STATUS_CHOICES,
)
from events.models import TicketType, RSVP
from qr_codes.models import QRCode
from ..models import EventPaymentBill, Transaction, TransactionOfOrganizer
from .serializers import (
    CardInformationSerializer,
    EventPaymentBillSerializer,
    TransactionOfOrganizerSerializer,
    TransactionSerializer,
)

stripe.api_key = config("STRIPE_SECRET_KEY")


class EventPaymentBillListView(generics.ListAPIView):
    queryset = EventPaymentBill.objects.all()
    serializer_class = EventPaymentBillSerializer


class EventPaymentBillDetailView(generics.RetrieveAPIView):
    queryset = EventPaymentBill.objects.all()
    serializer_class = EventPaymentBillSerializer


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
    To buy tickets - [(event_id, ticket_id), quantity of tickets]

    {
        "event_id": 5,
        "ticket_id": 4,
        "quantity": 1
    }
    """

    serializer_class = None

    def post(self, request, *args, **kwargs):
        data = request.data
        event_id = data.get("event_id")
        ticket_id = data.get("ticket_id")
        quantity = data.get("quantity")

        if not (event_id and ticket_id and quantity):
            raise NotAcceptable(
                "Please provide event_id, ticket_id, and quantity in the request."
            )

        try:
            ticket_obj = TicketType.objects.get(
                id=ticket_id, event__id=event_id
            )
        except TicketType.DoesNotExist:
            raise NotFound("Ticket not found for the given event.")

        if not ticket_obj.stripe_price_id:
            return Response(
                {"error": "Stripe price ID is missing for the ticket."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            checkout_session = stripe.checkout.Session.create(
                line_items=[
                    {
                        "price": ticket_obj.stripe_price_id,
                        "quantity": quantity,
                    },
                ],
                payment_method_types=[
                    "card",
                ],
                mode="payment",
                success_url=settings.SITE_URL
                + "/?success=true&session_id={CHECKOUT_SESSION_ID}",
                cancel_url=settings.SITE_URL + "/?canceled=true",
            )
        except stripe.error.StripeError:
            return Response(
                {"error": "Something went wrong in payment session"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        rsvp_obj = rsvp_create(ticket_obj, request.user)
        transaction_obj = transaction_create(
            checkout_session, ticket_obj, rsvp_obj, quantity
        )
        link_with_qrcode(transaction_obj)

        return redirect(checkout_session.url)


def rsvp_create(ticket_obj, user):
    return RSVP.objects.create(event=ticket_obj.event, attendee=user)


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


def link_with_qrcode(transaction_obj):
    code_data = f"""//////
{transaction_obj.ticket_type.name}-
{transaction_obj.currency}-
{transaction_obj.amount}-
{transaction_obj.quantity}-
{transaction_obj.payment_status}-
{transaction_obj.rsvp.id}-
{transaction_obj.transaction_id}
//////
"""
    qr_obj = QRCode.objects.create(
        transaction=transaction_obj, code_data=code_data
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
