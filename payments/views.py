from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from payments.models import Payment
from payments.serializers import PaymentSerializer, PaymentSuccessSerializer
from payments.services import set_payment_status_paid


class PaymentsViewSet(ReadOnlyModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if not user.is_superuser:
            queryset = queryset.filter(borrowing__user_id=user.id)
        return queryset

    @action(
        methods=["GET", ],
        detail=False,
        url_path="success",
    )
    def success(self, request):
        """Endpoint for success payment"""
        serializer = PaymentSuccessSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data.get("session_id")

        if (e := set_payment_status_paid(session_id)) is True:

            return Response("Payment Successful", status=status.HTTP_200_OK)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


