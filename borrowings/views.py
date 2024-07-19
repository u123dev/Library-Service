from django.db import transaction
from django.shortcuts import render, redirect
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter, inline_serializer
from rest_framework import viewsets, status, mixins, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingSerializer,
    BorrowingCreateSerializer,
    BorrowingReturnSerializer,
    BorrowingDetailSerializer
)
from borrowings.services import pending_count
from borrowings.tasks import check_overdue
from notifications.services import bot
from payments.services import create_payment_stripe_checkout_session, create_fine_stripe_checkout_session


@extend_schema_view(
    list=extend_schema(
        summary="List of all borrowings",
        parameters=[
            OpenApiParameter(
                "user_id",
                type=OpenApiTypes.INT,
                description="Filter by user id "
                "(ex. ?user_id=value). ",
            ),
            OpenApiParameter(
                "is_active",
                type=OpenApiTypes.STR,
                required=False,
                description="Filter by active borrowings "
                            "(ex. ?is_active=value - for borrowings still not returned "
                            "or nothing - for all borrowings).",
            ),
        ]
    ),
    create=extend_schema(
        summary="Add new borrowing",
    ),
    retrieve=extend_schema(
        summary="Get borrowing object by id",
        parameters=[
            OpenApiParameter(
                "page",
                type=OpenApiTypes.STR,
                description="Page related payments "
                            "(ex. ?page=value ) "
            ),
        ]

    ),
    return_borrowing=extend_schema(
        summary="Return borrowing by id",
    ),
    overdue=extend_schema(
        summary="Check overdue borrowings ( only for Admin users )",
        responses={
            status.HTTP_200_OK: inline_serializer(
                name="Overdue",
                fields={"Overdue": serializers.IntegerField(default=8)}
            ),
        }
    ),
    pending=extend_schema(
        summary="Check pending payments count",
        responses={
            status.HTTP_200_OK: inline_serializer(
                name="Pending",
                fields={
                    "Pending": serializers.IntegerField(default=25),
                    "user_id": serializers.IntegerField(default=1),
                }
            ),
        },
    ),
)
class BorrowingsViewSet(mixins.CreateModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        GenericViewSet):
    queryset = Borrowing.objects.all()
    permission_classes = (IsAuthenticated, )

    def get_serializer_class(self):
        if self.action in ("create", ):
            return BorrowingCreateSerializer
        if self.action in ("retrieve", ):
            return BorrowingDetailSerializer
        if self.action == "return_borrowing":
            return BorrowingReturnSerializer
        return BorrowingSerializer

    def get_queryset(self):
        queryset = self.queryset.select_related("book", "user").prefetch_related("payments")

        if not self.request.user.is_staff:
            queryset = queryset.filter(user_id=self.request.user.id)

        user_id = self.request.query_params.get("user_id")
        if user_id and self.request.user.is_staff:
            queryset = queryset.filter(user_id=user_id)

        is_active = self.request.query_params.get("is_active")
        if is_active:
            queryset = queryset.filter(actual_return_date__isnull=True)

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if (count := pending_count(request.user)) > 0:
            return Response(
                {"Borrowing" : "Is not allowed.", "Count of pending payments" : count},
                status=status.HTTP_403_FORBIDDEN
            )

        with transaction.atomic():
            serializer.save()

            borrowing = Borrowing.objects.get(pk=serializer["id"].value)
            book = borrowing.book
            book.inventory -= 1
            book.save()

            payment = create_payment_stripe_checkout_session(borrowing, self.request)

        return redirect(payment.session_url)

    @action(
        methods=["POST", ],
        detail=True,
        url_path="return",
    )
    def return_borrowing(self, request, pk=None):
        """Endpoint for returning borrowing"""
        borrowing = self.get_object()
        serializer = self.get_serializer(borrowing, data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            serializer.save()

            book = borrowing.book
            book.inventory += 1
            book.save()

            payment_fine = create_fine_stripe_checkout_session(borrowing, self.request)

        bot.send_message(f"*Return* Borrowing id: {borrowing.id} \n"
                         f"Book: {borrowing.book} \n"
                         f"User: {borrowing.user} \n")

        if payment_fine:
            return redirect(payment_fine.session_url)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=["GET", ],
        detail=False,
        url_path="overdue",
        permission_classes=[IsAdminUser, ]
    )
    def overdue(self, request, pk=None):
        """Endpoint for check overdue borrowings"""
        result = {"Overdue": check_overdue()}
        return Response(result, status=status.HTTP_200_OK)

    @action(
        methods=["GET", ],
        detail=False,
        url_path="pending",
    )
    def pending(self, request, pk=None):
        """Endpoint for check the number of pending payments for current user"""
        result = {"Pending": pending_count(request.user),
                  "user_id": request.user.id, }
        return Response(result, status=status.HTTP_200_OK)
