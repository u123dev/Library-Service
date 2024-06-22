import stripe


from borrowings.models import Borrowing
from library_service.settings import STRIPE_API_KEY
from payments.models import Payment

stripe.api_key = STRIPE_API_KEY


def create_stripe_checkout_session(borrowing: Borrowing) -> Payment:
    days = (borrowing.expected_return_date - borrowing.borrow_date).days + 1
    total_price = borrowing.book.daily_fee * days

    success_url = ""
    cancel_url = ""

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

