from borrowings.models import Borrowing
from payments.models import Payment
from users.models import User


def pending_count(reader: User):
    count = Borrowing.objects.filter(user=reader).filter(payments__status=Payment.StatusType.PENDING).count()
    return count


def detail_borrowing_info(instance):
    return (f"Borrowing id: {instance.id}\n"
            f"Book: {instance.book}\n"
            f"User: {instance.user}\n"
            f"Date: {instance.borrow_date}\n"
            f"Expected Return: {instance.expected_return_date}")
