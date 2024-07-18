from datetime import timedelta
from unittest.mock import patch

from django.shortcuts import get_object_or_404
from django.test import TestCase

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from tests.init_mock_classes import Session_Mock, Session_Mock_not_paid, Session_Mock_expired
from tests.init_sample import (
    init_sample_user,
    init_sample_book,
    init_sample_admin_user,
    init_sample_borrowing,
    init_sample_payment
)
from notifications.services import TelegramSender
from payments.models import Payment
from payments.serializers import PaymentSerializer


BORROWING_URL = reverse("borrowings:borrowing-list")

PAYMENT_URL = reverse("payments:payment-list")
PAYMENT_DETAIL_URL = "payments:payment-detail"
PAYMENT_RENEW_URL = "payments:payment-renew"

PAYMENT_SUCCESS_URL = reverse("payments:payment-success") + "?session_id="
PAYMENT_CANCEL_URL = reverse("payments:payment-cancel")
PAYMENT_CHECK_EXPIRED_URL = reverse("payments:payment-check-expired")


def detail_url(url, instance_id):
    return reverse(url, args=[instance_id])


class ModelPaymentTests(TestCase):
    def setUp(self):
        self.user1 = init_sample_user(1)
        self.book1 = init_sample_book()
        self.borrowing1 = init_sample_borrowing(self.book1, self.user1)
        self.payment1 = init_sample_payment(self.borrowing1)

    def test_payment_str_successfully(self):
        self.assertEqual(
            str(self.payment1),
            f"{self.payment1.type} : {self.payment1.status} "
            f"[ USD {self.payment1.money_to_pay} ] {self.payment1.borrowing}"
        )


class AnonymousUserPaymentAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

        self.user1 = init_sample_user(1)
        self.book1 = init_sample_book()
        self.borrowing1 = init_sample_borrowing(self.book1, self.user1)
        self.payment1 = init_sample_payment(self.borrowing1)

        self.payload = {
            "borrowing": self.borrowing1,
            "money_to_pay": 10,
        }

    def test_anonymous_user_payment_list(self):
        response = self.client.get(PAYMENT_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_user_payment_post_unathorized(self):
        response = self.client.post(PAYMENT_URL, self.payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_user_payment_detail(self):
        response = self.client.get(detail_url(PAYMENT_DETAIL_URL, self.payment1.pk))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PaymentAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = init_sample_user(1)
        self.client.force_authenticate(self.user1)

        self.book1 = init_sample_book()
        self.borrowing1 = init_sample_borrowing(self.book1, self.user1)

        self.payload = {
            "borrowing": self.borrowing1,
            "money_to_pay": 10,
        }

    def test_non_admin_user_payment_list(self):
        response = self.client.get(PAYMENT_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        payments = Payment.objects.all()
        serializer = PaymentSerializer(payments, many=True)
        self.assertEqual(response.data.get("results"), serializer.data)

    def test_non_admin_user_payment_post_not_allowed(self):
        response = self.client.post(PAYMENT_URL, self.payload)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_non_admin_user_payment_detail(self):
        self.payment1 = init_sample_payment(self.borrowing1)
        response = self.client.get(detail_url(PAYMENT_DETAIL_URL, self.payment1.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        serializer = PaymentSerializer(self.payment1)
        self.assertEqual(response.data, serializer.data)

    def test_non_admin_user_payment_put_not_allowed(self):
        self.payment1 = init_sample_payment(self.borrowing1)
        response = self.client.put(detail_url(PAYMENT_DETAIL_URL, self.payment1.pk), self.payload)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_non_admin_user_filter_own_payments(self):
        response = self.client.get(PAYMENT_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        payments = Payment.objects.filter(borrowing__user=self.user1)
        serializer = PaymentSerializer(payments, many=True)
        self.assertEqual(response.data.get("results"), serializer.data)

    @patch("payments.services._create_stripe_checkout_session", Session_Mock)
    def test_create_borrowing_payment(self):

        self.payload = {
            "borrow_date": timezone.now().date(),
            "expected_return_date": timezone.now().date() + timedelta(days=1),
            "actual_return_date": "",
            "book": self.book1.id,
            "user": self.user1,
        }

        session = Session_Mock()

        response = self.client.post(BORROWING_URL, self.payload)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

        payments = Payment.objects.filter(borrowing__user=self.user1)
        serializer = PaymentSerializer(payments, many=True)

        self.assertEqual(session.url, serializer.data[0].get("session_url"))
        self.assertEqual(session.id, serializer.data[0].get("session_id"))

    @patch.object(TelegramSender, "send_message")
    @patch("payments.services.stripe.checkout.Session.retrieve", Session_Mock)
    def test_payment_success_correct_session_id(self, mock_method):
        self.payment1 = init_sample_payment(self.borrowing1, session_id="111")
        success_url = PAYMENT_SUCCESS_URL + self.payment1.session_id

        session = Session_Mock()

        response = self.client.get(success_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_method.assert_called()

    @patch.object(TelegramSender, "send_message")
    @patch("payments.services.stripe.checkout.Session.retrieve", Session_Mock_not_paid)
    def test_payment_success_bad_session_id_error(self, mock_method):
        self.payment1 = init_sample_payment(self.borrowing1, session_id="111")
        success_url = PAYMENT_SUCCESS_URL + self.payment1.session_id

        session = Session_Mock_not_paid()

        response = self.client.get(success_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_payment_cancel(self):
        response = self.client.get(PAYMENT_CANCEL_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_payment_renew_already_paid(self):
        self.payment1 = init_sample_payment(self.borrowing1, status=Payment.StatusType.PAID)
        response = self.client.get(detail_url(PAYMENT_RENEW_URL, self.payment1.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("paid", response.data)

    def test_payment_renew_pending(self):
        self.payment1 = init_sample_payment(self.borrowing1,
                                            status=Payment.StatusType.PENDING,
                                            session_url="http://test.test")
        response = self.client.get(detail_url(PAYMENT_RENEW_URL, self.payment1.pk))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    @patch.object(TelegramSender, "send_message")
    @patch("payments.services.stripe.checkout.Session.create", Session_Mock_not_paid)
    def test_payment_renew_expired(self, mock_method):
        self.payment1 = init_sample_payment(self.borrowing1,
                                            status=Payment.StatusType.EXPIRED,
                                            session_url="http://test.test")
        session_mock = Session_Mock()
        response = self.client.get(detail_url(PAYMENT_RENEW_URL, self.payment1.pk))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

        payment = get_object_or_404(Payment, id=self.payment1.pk)
        self.assertEqual(payment.status, Payment.StatusType.PENDING)
        self.assertEqual(payment.session_url, "http://test.url")

    def test_payment_check_expired_non_admin_forbidden(self):
        response = self.client.get(PAYMENT_CHECK_EXPIRED_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch.object(TelegramSender, "send_message")
    @patch("payments.services.stripe.checkout.Session.retrieve", Session_Mock_expired)
    def test_payment_check_expired_admin(self, mock_method):
        self.user2 = init_sample_admin_user(2)
        self.client.force_authenticate(self.user2)

        self.payment1 = init_sample_payment(self.borrowing1,
                                            status=Payment.StatusType.PENDING, )

        session = Session_Mock_not_paid()

        response = self.client.get(PAYMENT_CHECK_EXPIRED_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        payment = get_object_or_404(Payment, id=self.payment1.pk)
        self.assertEqual(payment.status, Payment.StatusType.EXPIRED)
