from django.shortcuts import render, redirect
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from payments.models import Payment
from payments.serializers import PaymentSerializer, PaymentSuccessSerializer
from payments.services import set_payment_status_paid, renew_stripe_checkout_session
from payments.tasks import check_expired_session


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


    @action(
        methods=["GET", ],
        detail=False,
        url_path="cancel",
    )
    def cancel(self, request):
        """Endpoint for cancel payment"""

        return Response(
            "Payment can be paid later. Session is available for only 24h.",
            status=status.HTTP_200_OK
        )


    @action(
        methods=["GET", ],
        detail=False,
        url_path="check_expired",
    )
    def check_expired(self, request):
        """Endpoint for check all expired payment sessions"""
        res = check_expired_session()
        return Response(res, status=status.HTTP_200_OK)

    @action(
        methods=["GET", ],
        detail=True,
        url_path="check_expired",
    )
    def renew(self, request, pk=None):
        """Endpoint for renew payment session, if expired. Otherwise - redirect"""
        payment = get_object_or_404(Payment, pk=pk)
        status = payment.status

        if status == Payment.StatusType.PAID:
            return Response("Payment is already paid")

        if status == Payment.StatusType.PENDING:
            return redirect(payment.session_url)

        # status == Payment.StatusType.EXPIRED
        new_payment = renew_stripe_checkout_session(payment, request)
        print(new_payment.session_url)

        return redirect(new_payment.session_url)
