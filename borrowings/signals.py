from django.db.models.signals import post_save
from django.dispatch import receiver

from borrowings.models import Borrowing
from borrowings.services import detail_borrowing_info
from notifications.services import bot


@receiver(post_save, sender=Borrowing)
def send_msg_after_create(sender, instance, created, **kwargs):
    if created:
        message = f"*Borrowing has been created.* \n{detail_borrowing_info(instance)}"
        bot.send_message(message)
