from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ErrorDetail
from rest_framework.test import APITestCase, APIClient

from borrowings.models import Borrowing
from borrowings.serializers import BorrowingSerializer, BorrowingDetailSerializer
from borrowings.services import pending_count
from borrowings.tasks import check_overdue
from tests.init_mock_classes import Session_Mock
from tests.init_sample import (
    init_sample_user,
    init_sample_book,
    init_sample_admin_user,
    init_sample_borrowing,
    init_sample_payment
)
from notifications.services import TelegramSender
from payments.models import Payment

BORROWING_URL = reverse("borrowings:borrowing-list")
BORROWING_DETAIL_URL = "borrowings:borrowing-detail"
BORROWING_RETURN_URL = "borrowings:borrowing-return-borrowing"
BORROWING_OVERDUE_URL = reverse("borrowings:borrowing-overdue")
BORROWING_PENDING_URL = reverse("borrowings:borrowing-pending")


def detail_url(url, instance_id):
    return reverse(url, args=[instance_id])


class ModelBorrowingTests(TestCase):
    def setUp(self):
        self.user1 = init_sample_user(1)
        self.book1 = init_sample_book()
        self.borrowing1 = init_sample_borrowing(self.book1, self.user1)

    def test_borrowing_str_successfully(self):
        self.assertEqual(
            str(self.borrowing1),
            f"id: {self.borrowing1.id} | book: "
            f"{str(self.book1)}"
            f" borrowed: {str(timezone.now().date())} by: test-1@test.com"
        )


class AnonymousUserBorrowingAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

        self.user1 = init_sample_user(1)
        self.book1 = init_sample_book()
        self.borrowing1 = init_sample_borrowing(self.book1, self.user1)

        self.payload = {
            "borrow_date": timezone.now().date(),
            "expected_return_date": timezone.now().date() + timedelta(days=1),
            "actual_return_date": "",
            "book": self.book1,
            "user": self.user1,
        }

    def test_anonymous_user_borrowing_list(self):
        response = self.client.get(BORROWING_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_user_borrowing_post_unathorized(self):
        response = self.client.post(BORROWING_URL, self.payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_user_borrowing_detail(self):
        response = self.client.get(detail_url(BORROWING_DETAIL_URL, self.borrowing1.pk))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class BorrowingAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = init_sample_user(1)
        self.client.force_authenticate(self.user1)

        self.book1 = init_sample_book()
        self.borrowing1 = init_sample_borrowing(self.book1, self.user1)

        self.payload = {
            "borrow_date": timezone.now().date(),
            "expected_return_date": timezone.now().date() + timedelta(days=1),
            "actual_return_date": "",
            "book": self.book1.id,
            "user": self.user1,
        }

    def test_non_admin_user_borrowing_list(self):
        response = self.client.get(BORROWING_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        borrowings = Borrowing.objects.all()
        serializer = BorrowingSerializer(borrowings, many=True)
        self.assertEqual(response.data.get("results"), serializer.data)

    @patch("payments.services._create_stripe_checkout_session", Session_Mock)
    def test_non_admin_user_borrowing_post(self):
        response = self.client.post(BORROWING_URL, self.payload)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_non_admin_user_borrowing_detail(self):
        response = self.client.get(detail_url(BORROWING_DETAIL_URL, self.borrowing1.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        serializer = BorrowingDetailSerializer(self.borrowing1)
        self.assertEqual(response.data, serializer.data)

    def test_non_admin_user_borrowing_put_forbidden(self):
        response = self.client.put(detail_url(BORROWING_DETAIL_URL, self.borrowing1.pk), self.payload)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_non_admin_user_filter_own_borrowing(self):
        response = self.client.get(BORROWING_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        borrowings = Borrowing.objects.filter(user=self.user1)
        serializer = BorrowingSerializer(borrowings, many=True)
        self.assertEqual(response.data.get("results"), serializer.data)

    def test_create_borrowing_zero_inventory_book_error(self):
        self.book2 = init_sample_book(title="Book2", inventory=0)

        self.payload = {
            "borrow_date": timezone.now().date(),
            "expected_return_date": timezone.now().date() + timedelta(days=1),
            "actual_return_date": "",
            "book": self.book2.id,
            "user": self.user1,
        }

        response = self.client.post(BORROWING_URL, self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIsInstance(response.data["book"][0], ErrorDetail)

    def test_create_borrowing_expected_return_date_lt_today_error(self):
        self.payload = {
            "borrow_date": timezone.now().date(),
            "expected_return_date": timezone.now().date() - timedelta(days=1),
            "actual_return_date": "",
            "book": self.book1.id,
            "user": self.user1,
        }

        response = self.client.post(BORROWING_URL, self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIsInstance(response.data["expected_return_date"][0], ErrorDetail)

    def test_create_borrowing_pending_payments_non_zero_forbidden(self):
        init_sample_payment(self.borrowing1)
        init_sample_payment(self.borrowing1)

        response = self.client.post(BORROWING_URL, self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(response.data["Borrowing"], "Is not allowed.")

    @patch("payments.services._create_stripe_checkout_session", Session_Mock)
    def test_borrowing_book_inventory_decrement(self):
        inventory_before = self.book1.inventory
        response = self.client.post(BORROWING_URL, self.payload)

        self.book1.refresh_from_db()
        inventory_after = self.book1.inventory

        self.assertEqual(inventory_before - inventory_after, 1)

    def test_borrowing_book_inventory_increment(self):
        inventory_before = self.book1.inventory

        payload = {"actual_return_date": timezone.now().date() + timedelta(days=1), }
        response = self.client.post(detail_url(BORROWING_RETURN_URL, self.borrowing1.pk), payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.book1.refresh_from_db()
        inventory_after = self.book1.inventory

        self.assertEqual(inventory_after - inventory_before, 1)

    def test_borrowing_book_return_without_payment(self):
        payload = {"actual_return_date": timezone.now().date() + timedelta(days=1), }
        response = self.client.post(detail_url(BORROWING_RETURN_URL, self.borrowing1.pk), payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_borrowing_book_return_with_fine_payment(self):
        payload = {"actual_return_date": timezone.now().date() + timedelta(days=2), }
        response = self.client.post(detail_url(BORROWING_RETURN_URL, self.borrowing1.pk), payload)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_borrowing_book_return_date_not_none_error(self):
        self.borrowing1.actual_return_date = self.borrowing1.expected_return_date
        self.borrowing1.save()

        payload = {"actual_return_date": timezone.now().date() + timedelta(days=1), }
        response = self.client.post(detail_url(BORROWING_RETURN_URL, self.borrowing1.pk), payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIsInstance(response.data["actual_return_date"][0], ErrorDetail)

    def test_borrowing_book_return_date_lt_today_error(self):
        self.borrowing1.borrow_date = timezone.now().date() - timedelta(days=2)
        self.borrowing1.save()

        payload = {"actual_return_date": timezone.now().date() - timedelta(days=1), }
        response = self.client.post(detail_url(BORROWING_RETURN_URL, self.borrowing1.pk), payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIsInstance(response.data["actual_return_date"][0], ErrorDetail)

    def test_borrowing_book_return_with_blank_return_date_as_today(self):
        payload = {}
        response = self.client.post(detail_url(BORROWING_RETURN_URL, self.borrowing1.pk), payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.borrowing1.refresh_from_db()
        serializer = BorrowingDetailSerializer(self.borrowing1)
        self.assertEqual(response.data["actual_return_date"], serializer.data["actual_return_date"])


class AdminUserBorrowingAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = init_sample_admin_user(1)
        self.client.force_authenticate(self.user1)

        self.book1 = init_sample_book()
        self.borrowing1 = init_sample_borrowing(self.book1, self.user1)

        self.payload = {
            "borrow_date": timezone.now().date(),
            "expected_return_date": timezone.now().date() + timedelta(days=1),
            "actual_return_date": "",
            "book": self.book1.id,
            "user": self.user1,
        }

        self.user2 = init_sample_user(2)
        self.borrowing2 = init_sample_borrowing(self.book1, self.user2,
                                                actual_return_date=timezone.now().date() + timedelta(days=1))
        self.borrowing3 = init_sample_borrowing(self.book1, self.user2)

    def test_admin_user_borrowing_list(self):
        response = self.client.get(BORROWING_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        borrowings = Borrowing.objects.all()
        serializer = BorrowingSerializer(borrowings, many=True)
        self.assertEqual(response.data.get("results"), serializer.data)

    def test_admin_user_filter_borrowing_by_user(self):
        response = self.client.get(BORROWING_URL + f"?user_id={self.user2.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        borrowings = Borrowing.objects.filter(user=self.user2)
        serializer = BorrowingSerializer(borrowings, many=True)
        self.assertEqual(response.data.get("results"), serializer.data)

    def test_admin_user_filter_borrowing_by_active(self):
        response = self.client.get(BORROWING_URL + "?is_active=True")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        borrowings = Borrowing.objects.filter(actual_return_date__isnull=True)
        serializer = BorrowingSerializer(borrowings, many=True)
        self.assertEqual(response.data.get("results"), serializer.data)


class BorrowingTasksTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = init_sample_admin_user(1)
        # self.client.force_authenticate(self.user1)

        self.book1 = init_sample_book()
        self.borrowing1 = init_sample_borrowing(self.book1, self.user1)

        self.user2 = init_sample_user(2)
        self.borrowing2 = init_sample_borrowing(self.book1, self.user2,
                                                actual_return_date=timezone.now().date() + timedelta(days=1))
        self.borrowing3 = init_sample_borrowing(self.book1, self.user2)

    @patch.object(TelegramSender, "send_message")
    def test_check_overdue_api_non_admin_forbidden(self, mock_method):
        self.client.force_authenticate(self.user2)

        response = self.client.get(BORROWING_OVERDUE_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch.object(TelegramSender, "send_message")
    def test_check_overdue_api_admin(self, mock_method):
        self.client.force_authenticate(self.user1)

        expected_borrowings_count = Borrowing.objects.filter(
            actual_return_date__isnull=True).filter(
            expected_return_date__lte=timezone.now().date() + timedelta(days=1)).order_by(
            "borrow_date").count()

        response = self.client.get(BORROWING_OVERDUE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(list(response.data.values()), [expected_borrowings_count, ])
        mock_method.assert_called()

    @patch.object(TelegramSender, "send_message")
    def test_check_overdue_task_gt_0(self, mock_method):
        expected_borrowings_count = Borrowing.objects.filter(
            actual_return_date__isnull=True).filter(
            expected_return_date__lte=timezone.now().date() + timedelta(days=1)).order_by(
            "borrow_date").count()
        borrowings_count = check_overdue()
        self.assertGreater(borrowings_count, 0)
        self.assertEqual(expected_borrowings_count, borrowings_count)

        mock_method.assert_called()

    @patch.object(TelegramSender, "send_message")
    def test_check_overdue_task_eq_0(self, mock_method):
        self.borrowing1.expected_return_date = timezone.now().date() + timedelta(days=3)
        self.borrowing1.save()
        self.borrowing3.expected_return_date = timezone.now().date() + timedelta(days=3)
        self.borrowing3.save()

        expected_borrowings_count = Borrowing.objects.filter(
            actual_return_date__isnull=True).filter(
            expected_return_date__lte=timezone.now().date() + timedelta(days=1)).order_by(
            "borrow_date").count()
        borrowings_count = check_overdue()
        self.assertEqual(borrowings_count, 0)
        self.assertEqual(expected_borrowings_count, borrowings_count)

        mock_method.assert_called()

    def test_pending_count_api_user(self):
        self.client.force_authenticate(self.user1)

        init_sample_payment(self.borrowing2, status=Payment.StatusType.PENDING)
        init_sample_payment(self.borrowing3, status=Payment.StatusType.PENDING)

        expected_pending_count = Borrowing.objects.filter(user=self.user1).filter(
            payments__status=Payment.StatusType.PENDING).count()

        response = self.client.get(BORROWING_PENDING_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(list(response.data.values()), [expected_pending_count, self.user1.id])

    def test_function_pending_count_gt_0(self):
        init_sample_payment(self.borrowing2, status=Payment.StatusType.PENDING)
        init_sample_payment(self.borrowing3, status=Payment.StatusType.PENDING)

        expected_pending_count = Borrowing.objects.filter(user=self.user2).filter(
            payments__status=Payment.StatusType.PENDING).count()

        current_pending_count = pending_count(self.user2)
        self.assertGreater(expected_pending_count, 0)
        self.assertEqual(expected_pending_count, current_pending_count)

    def test_function_pending_count_eq_0(self):
        init_sample_payment(self.borrowing2, status=Payment.StatusType.PAID)
        init_sample_payment(self.borrowing3, status=Payment.StatusType.PAID)

        expected_pending_count = Borrowing.objects.filter(user=self.user2).filter(
            payments__status=Payment.StatusType.PENDING).count()

        current_pending_count = pending_count(self.user2)
        self.assertEqual(expected_pending_count, 0)
        self.assertEqual(expected_pending_count, current_pending_count)
