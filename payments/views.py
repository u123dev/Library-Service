from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from payments.models import Payment
from payments.serializers import PaymentSerializer


class PaymentsViewSet(ReadOnlyModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    # permission_classes = (IsAuthenticated,)
