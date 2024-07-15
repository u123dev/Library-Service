from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from books.models import Book
from borrowings.models import Borrowing
from payments.models import Payment


def init_sample_user(number: int):
    return get_user_model().objects.create_user(
        email=f"test-{str(number)}@test.com",
        password="testpass",
    )


def init_sample_admin_user(number: int):
    return get_user_model().objects.create_superuser(
        email=f"test-{str(number)}@test.com",
        password="testpass",
        is_superuser=True,
    )


def init_sample_book(**params):
    defaults = {
        "title": "Sample_book1",
        "author": "Author1",
        "cover": Book.CoverType.SOFT,
        "inventory": 11,
        "daily_fee": 10.34,
    }
    defaults.update(params)
    return Book.objects.create(**defaults)


def init_sample_borrowing(book, user, **params):
    defaults = {
        "borrow_date": timezone.now().date(),
        "expected_return_date": timezone.now().date() + timedelta(days=1),
        "actual_return_date": None,
        "book": book,
        "user": user,
    }
    defaults.update(params)
    return Borrowing.objects.get_or_create(**defaults)[0]


def init_sample_payment(borrowing, **params):
    defaults = {
        "borrowing": borrowing,
        "money_to_pay": 10,
    }
    defaults.update(params)
    return Payment.objects.get_or_create(**defaults)[0]
