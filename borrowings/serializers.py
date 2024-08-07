from datetime import datetime

from rest_framework import serializers, pagination
from rest_framework.utils.serializer_helpers import ReturnList

from borrowings.models import Borrowing
from payments.models import Payment
from payments.serializers import PaymentSerializer


class BorrowingSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field="email", read_only=True)
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


class BorrowingDetailSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field="email", read_only=True)
    book = serializers.StringRelatedField()
    payments = serializers.SerializerMethodField("borrowing_payments")

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

    def borrowing_payments(self, obj) -> ReturnList:
        ''' Pggination by related payments'''
        payments = Payment.objects.filter(borrowing=obj).order_by("borrowing__borrow_date")
        if self.context.get("request"):
            paginator = pagination.PageNumberPagination()
            page = paginator.paginate_queryset(payments, self.context["request"])
            serializer = PaymentSerializer(page, many=True, context={"request": self.context["request"]})
        else:
            serializer = PaymentSerializer(payments, many=True)
        return serializer.data


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


class BorrowingReturnSerializer(serializers.ModelSerializer):

    class Meta:
        model = Borrowing
        fields = ("id", "actual_return_date", )

    def validate_actual_return_date(self, value):
        if self.instance.actual_return_date is not None:
            raise serializers.ValidationError("Borrowing already returned.")
        if value and value < datetime.now().date():
            raise serializers.ValidationError("Actual return date must not be less than today.")
        return value

    def validate(self, attrs):
        if not attrs.get("actual_return_date"):
            attrs["actual_return_date"] = datetime.now().date()
        return attrs
