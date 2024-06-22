from django.db.models.signals import post_save
from django.dispatch import receiver

from notifications.services import bot
from payments.models import Payment


@receiver(post_save, sender=Payment)
def send_msg_after_create(sender, instance, created, **kwargs):
    if created:
        message = (f"*Payment Checkout has been created.* \n"
                   f"Amount: {instance.money_to_pay}\n"
                   f"Borrowing id: {instance.borrowing.id} | Book: {instance.borrowing.book.title} | "
                   f"User: {instance.borrowing.user}\n"
                   f"From: {instance.borrowing.borrow_date} To: {instance.borrowing.expected_return_date}\n"
                   f"Status: {instance.type} : {instance.status}")
        bot.send_message(message)
