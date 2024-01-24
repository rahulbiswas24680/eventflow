from django.urls import path

from .views import (
    TransactionListCreateView,
    TransactionDetailView,
    TicketCheckoutApiView
)

urlpatterns = [

    path('transactions/',
         TransactionListCreateView.as_view(),
         name='transaction-list'
         ),
    path('transactions/<int:pk>/',
         TransactionDetailView.as_view(),
         name='transaction-detail'
         ),
    path('ticket-checkout-session/', TicketCheckoutApiView.as_view(), name='ticket_payment')

]
