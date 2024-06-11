from django.db import transaction
from rest_framework import serializers

from books.models import Book
from books.serializers import BookSerializer
from borrowings.models import Borrowing


class BorrowingSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field="email", read_only=True)
    # book = BookSerializer(read_only=True)
    book = serializers.StringRelatedField()

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
        )
        read_only_fields = ("is_active", )


class BorrowingCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Borrowing
        fields = ("id", "book", "user", "borrow_date", "expected_return_date", "actual_return_date", )

    def validate_book(self, data):
        if data.inventory < 1:
            raise serializers.ValidationError(
                "The book you are borrowing cannot be borrowed."
            )
        return data

    def create(self, validated_data):
        with transaction.atomic():
            borrowings = Borrowing.objects.create(**validated_data)

            book = validated_data.pop("book")
            book.inventory -= 1
            book.save()

        return borrowings
