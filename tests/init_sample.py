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
