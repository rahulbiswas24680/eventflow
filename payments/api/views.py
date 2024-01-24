
from rest_framework import generics, filters, permissions, status
from ..models import Transaction
from .serializers import TransactionSerializer, CardInformationSerializer
import stripe
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from decouple import config
from django.shortcuts import redirect


class TransactionListCreateView(generics.ListCreateAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer


class TransactionDetailView(generics.RetrieveAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer


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


stripe.api_key = config('STRIPE_SECRET_KEY')


class TicketCheckoutApiView(APIView):
    """
    To buy tickets - [(event_id, ticket_id), quantity of tickets]
    """

    def post():
        try:
            checkout_session = stripe.checkout.Session.create(
                line_items=[
                    {
                        # should be dynamically created
                        'price': 'price_1ObglkSE7WiyHfjrwTLY4jZN',
                        'quantity': 1,
                    },
                ],
                payment_method_types=['card'],
                mode='payment',
                success_url=settings.SITE_URL +
                '/?success=true&session_id={CHECKOUT_SESSION_ID}',
                cancel_url=settings.SITE_URL + '/?canceled=true',
            )
        except:
            return Response(
                {'error': 'Something went wrong in payment session'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return redirect(checkout_session.url)
