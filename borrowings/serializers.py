from datetime import datetime

from django.db import transaction
from rest_framework import serializers

from books.models import Book
from books.serializers import BookSerializer
from borrowings.models import Borrowing
from payments.models import Payment
from payments.serializers import PaymentSerializer
from payments.services import create_payment_stripe_checkout_session, create_fine_stripe_checkout_session


class BorrowingSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field="email", read_only=True)
    # book = BookSerializer(read_only=True)
    book = serializers.StringRelatedField()
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "book",
            "user",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "is_active",
            "payments",
        )
        read_only_fields = ("is_active", )


class BorrowingCreateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Borrowing
        fields = ("id", "book", "user", "borrow_date", "expected_return_date", )

    def validate_expected_return_date(self, data):
        if data < datetime.today().date():
            raise serializers.ValidationError("Expected return date must be at least today.")
        return data

    def validate_book(self, data):
        if data.inventory < 1:
            raise serializers.ValidationError("The book cannot be borrowed: inventory=0.")
        return data

    def create(self, validated_data):
        with transaction.atomic():
            borrowing = Borrowing.objects.create(**validated_data)

            book = validated_data.pop("book")
            book.inventory -= 1
            book.save()

            payment = create_payment_stripe_checkout_session(borrowing, self.context["request"])

        return borrowing


class BorrowingReturnSerializer(serializers.ModelSerializer):

    class Meta:
        model = Borrowing
        fields = ("id", "actual_return_date", )

    def validate_actual_return_date(self, value):
        if self.instance.actual_return_date is not None:
            raise serializers.ValidationError("Borrowing already returned.")
        if value and value <= datetime.now().date():
            raise serializers.ValidationError("Actual return date must not be less than today.")
        return value

    def update(self, instance, validated_data):
        with transaction.atomic():
            if not validated_data.get("actual_return_date"):
                instance.actual_return_date = datetime.now().date()
            else:
                instance.actual_return_date = validated_data.pop("actual_return_date")
            instance.save()

            book = instance.book
            book.inventory += 1
            book.save()

            payment_fine = create_fine_stripe_checkout_session(instance, self.context["request"])

        return instance
