from rest_framework import serializers

from books.serializers import BookSerializer
from borrowings.models import Borrowing


class BorrowingSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field="email", read_only=True)
    book = BookSerializer(read_only=True)
    class Meta:
        model = Borrowing
        fields = ("id", "book", "user", "borrow_date", "expected_return_date", "actual_return_date", "is_active", )
        read_only_fields = ("is_active", )
