from datetime import datetime, timedelta

from celery.app import shared_task

from borrowings.models import Borrowing
from borrowings.services import detail_borrowing_info
from notifications.services import bot


@shared_task
def check_overdue() -> int:
    # filter(is_active=True)
    borrowings = Borrowing.objects.filter(
        actual_return_date__isnull=True
    ).filter(
        expected_return_date__lte=datetime.now().date() + timedelta(days=1)
    ).order_by("borrow_date").select_related()

    if borrowings_count := borrowings.count():
        msg = f"*Overdue borrowings qty = {borrowings_count}*"
        bot.send_message(msg)

        for borrowing in borrowings:
            bot.send_message(f"*Overdue* {detail_borrowing_info(borrowing)}")
    else:
        msg = "*No borrowings overdue today*"
        bot.send_message(msg)

    return borrowings_count
