
from rest_framework import generics
from ..models import QRCode
from .serializers import QRCodeSerializer


class QRCodeDetailView(generics.RetrieveAPIView):
    queryset = QRCode.objects.all()
    serializer_class = QRCodeSerializer
