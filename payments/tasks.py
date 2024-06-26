import stripe

from payments.models import Payment


def check_expired_session():
    '''Check Stripe Sessions for expiration'''

    payments = Payment.objects.filter(status=Payment.StatusType.PENDING)
    res = dict()
    for payment in payments:
        session_id = payment.session_id
        session = stripe.checkout.Session.retrieve(session_id)
        res[session_id] = session.status
        print(session_id, session.status)
    return res
