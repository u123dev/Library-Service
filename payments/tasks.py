from celery.app import shared_task

from payments.models import Payment
from payments.services import set_payment_status_expired


@shared_task
def check_expired_session():
    '''Check Stripe Sessions for expiration'''

    payments = Payment.objects.filter(status=Payment.StatusType.PENDING).select_related()
    res = {payment.session_id : payment.status
           for payment in payments if set_payment_status_expired(payment)}
    return res
