from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import CheckConstraint, Q, F

from books.models import Book


class Borrowing(models.Model):
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="borrowings")
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="borrowings")

    class Meta:
        constraints = [
            CheckConstraint(
                check=Q(actual_return_date__gte=F("borrow_date")),
                name="check_actual_date",
            ),
            CheckConstraint(
                check=Q(expected_return_date__gte=F("borrow_date")),
                name="check_expected_date",
            ),
        ]

    @property
    def is_active(self):
        return not bool(self.actual_return_date)

    def __str__(self):
        return f"id: {self.id} | book: {self.book} borrowed: {str(self.borrow_date)} by: {self.user}"
