from django.db.models.signals import post_save
from django.dispatch import receiver

from notifications.services import bot
from payments.models import Payment


@receiver(post_save, sender=Payment)
def send_msg_after_create(sender, instance, created, **kwargs):
    if created:
        if instance.type == Payment.Type.PAYMENT:
            date_from = instance.borrowing.borrow_date
            date_to = instance.borrowing.expected_return_date
        else:
            date_from = instance.borrowing.expected_return_date
            date_to = instance.borrowing.actual_return_date

        message = (f"*{instance.type.capitalize()} Checkout has been created.* \n"
                   f"Amount: {instance.money_to_pay}\n"
                   f"Borrowing id: {instance.borrowing.id} | Book: {instance.borrowing.book.title} | "
                   f"User: {instance.borrowing.user}\n"
                   f"From: {date_from} To: {date_to}\n"
                   f"Status: {instance.type} : {instance.status}")
        bot.send_message(message)

    if kwargs.get("update_fields") and "status" in kwargs.get("update_fields"):
        message = (f"*Payment Successful.* Amount: {instance.money_to_pay} | "
                   f"Borrowing id: {instance.borrowing.id}")
        bot.send_message(message)
