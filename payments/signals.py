from django.db.models.signals import post_save
from django.dispatch import receiver

from notifications.services import bot
from payments.models import Payment
from payments.services import detail_payment_info


@receiver(post_save, sender=Payment)
def send_msg_after_save(sender, instance, created, **kwargs):
    if created:
        message = detail_payment_info(instance)
        bot.send_message(message)

    if kwargs.get("update_fields") and "status" in kwargs.get("update_fields"):
        if instance.status == "paid":
            message = (f"*Payment Successful.* Amount: {instance.money_to_pay} | "
                       f"Borrowing id: {instance.borrowing.id}")
            bot.send_message(message)
        if instance.status == "expired":
            message = f"*Session Expired.* {instance.session_id}\n"\
                      f"*Borrowing id:* {instance.borrowing.id}"
            bot.send_message(message)
