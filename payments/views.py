from django.shortcuts import render, redirect
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from payments.models import Payment
from payments.serializers import PaymentSerializer, PaymentSuccessSerializer
from payments.services import set_payment_status_paid, renew_stripe_checkout_session
from payments.tasks import check_expired_session


@extend_schema_view(
    list=extend_schema(
        summary="List of all payments",
        parameters=[
            OpenApiParameter(
                "user_id",
                type=OpenApiTypes.INT,
                description="Filter by user id ( for Admin users ONLY ) "
                            "(ex. ?user_id=value). ",
            ),
        ]
    ),
    retrieve=extend_schema(
        summary="Get payments object by id",
    ),
    renew=extend_schema(
        summary="Renew payment session, if expired",
        responses={status.HTTP_200_OK: OpenApiResponse(description="")}
    ),
    success=extend_schema(
        summary="Success payment session",
        responses={
            status.HTTP_200_OK: PaymentSuccessSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Error payment session"),
        }
    ),
    cancel=extend_schema(
        summary="Cancel payment session",
        responses={status.HTTP_200_OK: OpenApiResponse(
            description="Payment can be paid later. Session is available for only 24h."
        )}
    ),
    check_expired=extend_schema(
        summary="Check expired payment sessions ( only for Admin users )",
        responses={status.HTTP_200_OK: OpenApiResponse(description="session_id : expired")}
    ),
)
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
        permission_classes=(IsAdminUser,)
    )
    def check_expired(self, request):
        """Endpoint for check all expired payment sessions"""
        res = check_expired_session()
        return Response(res, status=status.HTTP_200_OK)

    @action(
        methods=["GET", ],
        detail=True,
        url_path="renew",
    )
    def renew(self, request, pk=None):
        """Endpoint for renew payment session, if expired. Otherwise - redirect"""
        payment = get_object_or_404(Payment, pk=pk)
        status = payment.status

        if status == Payment.StatusType.PAID:
            return Response("Payment is already paid")

        if status == Payment.StatusType.PENDING:
            return redirect(payment.session_url)

        new_payment = renew_stripe_checkout_session(payment, request)

        return redirect(new_payment.session_url)
