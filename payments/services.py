import decimal
from decimal import Decimal

import stripe
from django.http import HttpRequest
from rest_framework.generics import get_object_or_404
from rest_framework.reverse import reverse

from borrowings.models import Borrowing
from library_service.settings import STRIPE_API_KEY
from payments.models import Payment

stripe.api_key = STRIPE_API_KEY


def _create_stripe_checkout_session(
        borrowing: Borrowing,
        sum: decimal,
        type: Payment.Type,
        request: HttpRequest
) -> Payment:

    success_url = request.build_absolute_uri(reverse("payments:payment-success")) + "?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = request.build_absolute_uri(reverse("payments:payment-cancel"))

    try:
        session = stripe.checkout.Session.create(
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Borrowing {type} for {borrowing.book.title}",
                    },
                    "unit_amount_decimal": sum * 100,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
        )

        payment = Payment.objects.create(
            type=type,
            borrowing=borrowing,
            session_url=session.url,
            session_id=session.id,
            money_to_pay=sum
        )
    except stripe.error.InvalidRequestError:
        payment = None

    return payment


def create_payment_stripe_checkout_session(borrowing: Borrowing, request: HttpRequest) -> Payment:
    days = (borrowing.expected_return_date - borrowing.borrow_date).days + 1
    total_price = borrowing.book.daily_fee * days
    return _create_stripe_checkout_session(borrowing, total_price, Payment.Type.PAYMENT, request)


def create_fine_stripe_checkout_session(borrowing: Borrowing, request: HttpRequest) -> Payment | None:
    overdue_days = max((borrowing.actual_return_date - borrowing.expected_return_date).days, 0)
    if overdue_days > 0:
        fine_price = borrowing.book.daily_fee * overdue_days * Decimal(Payment.FINE_MULTIPLIER)
        return _create_stripe_checkout_session(borrowing, fine_price, Payment.Type.FINE, request)
    return None


def set_payment_status_paid(session_id: str) -> bool | stripe.error.StripeError:
    try:
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status == "paid":
            payment = get_object_or_404(Payment, session_id=session_id)
            payment.status = Payment.StatusType.PAID
            payment.save(update_fields=["status"])
            return True

    except stripe.error.StripeError as e:
        return e

def set_payment_status_expired(payment: Payment) -> bool:
    ''' Set payment status Expired, if session is expired '''

    session_id = payment.session_id
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.status == "expired":
            payment.status = Payment.StatusType.EXPIRED
            payment.save(update_fields=["status"])
            return True

    except stripe.error.StripeError as e:
        pass

    return False

def detail_payment_info(instance: Payment) -> str:

    if instance.type == Payment.Type.PAYMENT:
        date_from = instance.borrowing.borrow_date
        date_to = instance.borrowing.expected_return_date
    else:
        date_from = instance.borrowing.expected_return_date
        date_to = instance.borrowing.actual_return_date

    return (f"*{instance.type.capitalize()} Checkout has been created.* \n"
            f"Amount: {instance.money_to_pay}\n"
            f"Borrowing id: {instance.borrowing.id} | Book: {instance.borrowing.book.title} | "
            f"User: {instance.borrowing.user}\n"
            f"From: {date_from} To: {date_to}\n"
            f"Status: {instance.type} : {instance.status}")
