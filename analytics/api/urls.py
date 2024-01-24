from django.urls import path

from .views import EventAnalyticsDetailView, TicketTypeAnalyticsDetailView

urlpatterns = [

    path('eventanalytics/<int:pk>/',
         EventAnalyticsDetailView.as_view(),
         name='eventanalytic-detail'
         ),

    path('ticketanalytics/<int:pk>/',
         TicketTypeAnalyticsDetailView.as_view(),
         name='ticketanalytic-detail'),

]
