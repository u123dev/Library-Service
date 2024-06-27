from payments.models import Payment
from payments.services import set_payment_status_expired


def check_expired_session():
    '''Check Stripe Sessions for expiration'''

    payments = Payment.objects.filter(status=Payment.StatusType.PENDING)
    res = {payment.session_id : payment.status
           for payment in payments if (status := set_payment_status_expired(payment))}
    return res
