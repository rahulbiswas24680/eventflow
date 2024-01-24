from django.urls import path
from .views import SupportTicketListCreateView

urlpatterns = [
    path('tickets/', SupportTicketListCreateView.as_view(), name='ticket-list'),
    path('tickets/create/', SupportTicketListCreateView.as_view(),
         name='ticket-create'),
]
