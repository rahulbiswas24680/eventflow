
from django.urls import path
from .views import QRCodeDetailView

urlpatterns = [
    path('qrcodes/<int:pk>/', QRCodeDetailView.as_view(), name='qrcode-detail'),
]