from django.urls import path

from .views import (
    EventsCheckoutAPIView,
    TransactionListCreateView,
    TransactionDetailView,
    TicketCheckoutApiView,
    stripe_webhook,
    transaction_qr
)

urlpatterns = [
    
    path('event/checkout/', EventsCheckoutAPIView.as_view(), name='event-checkout'),
    path('transactions/',
         TransactionListCreateView.as_view(),
         name='transaction-list'
         ),
    path('transactions/<int:pk>/',
         TransactionDetailView.as_view(),
         name='transaction-detail'
         ),
    path('ticket-checkout-session/', TicketCheckoutApiView.as_view(), name='ticket_payment'),
    path("webhook/stripe/", stripe_webhook, name="stripe-webhook"),
    path("transaction-qr/", transaction_qr, name="transaction-qr")

]
