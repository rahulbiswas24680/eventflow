import stripe
from decouple import config
from django.conf import settings
from django.shortcuts import redirect
from rest_framework import filters, generics, permissions, status
from rest_framework.exceptions import NotAcceptable
from rest_framework.response import Response
from rest_framework.views import APIView

from events.models import TicketType

from ..models import EventPaymentBill, Transaction, TransactionOfOrganizer
from .serializers import (CardInformationSerializer,
                          EventPaymentBillSerializer,
                          TransactionOfOrganizerSerializer,
                          TransactionSerializer)

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
        if "event_id" in data and "ticket_id" in data:
            try:
                ticket_obj = TicketType.objects.get(
                    id=data["ticket_id"], event__id=data["event_id"]
                )
            except TicketType.DoesNotExist:
                return Response(
                    {"error": "Ticket not found for the given event."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if ticket_obj.stripe_price_id:
                try:
                    checkout_session = stripe.checkout.Session.create(
                        line_items=[
                            {
                                "price": ticket_obj.stripe_price_id,
                                "quantity": data["quantity"],
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

                return redirect(checkout_session.url)
            else:
                return Response(
                    {"error": "Stripe price ID is missing for the ticket."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            raise NotAcceptable("Please check your input correctly.")


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
