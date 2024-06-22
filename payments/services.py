import stripe
from django.http import HttpRequest
from rest_framework.generics import get_object_or_404
from rest_framework.reverse import reverse

from borrowings.models import Borrowing
from library_service.settings import STRIPE_API_KEY
from payments.models import Payment

stripe.api_key = STRIPE_API_KEY


def create_stripe_checkout_session(borrowing: Borrowing, request: HttpRequest) -> Payment:
    days = (borrowing.expected_return_date - borrowing.borrow_date).days + 1
    total_price = borrowing.book.daily_fee * days

    success_url = request.build_absolute_uri(reverse("payments:payment-success"))
    cancel_url = request.build_absolute_uri(reverse("payments:payment-cancel"))

    try:
        session = stripe.checkout.Session.create(
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Borrowing payment for {borrowing.book.title}",
                    },
                    "unit_amount_decimal": total_price * 100,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
        )

        payment = Payment.objects.create(
            borrowing=borrowing,
            session_url=session.url,
            session_id=session.id,
            money_to_pay=total_price
        )
    except stripe.error.InvalidRequestError:
        payment = None

    return payment


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
