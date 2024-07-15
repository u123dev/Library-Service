from django.test import TestCase

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from books.models import Book
from books.serializers import BookSerializer
from tests.init_sample import (
    init_sample_user,
    init_sample_book,
    init_sample_admin_user
)

BOOK_URL = reverse("books:book-list")
BOOK_DETAIL_URL = "books:book-detail"


def detail_url(url, instance_id):
    return reverse(url, args=[instance_id])


class ModelBookTests(TestCase):
    def setUp(self):
        self.book1 = init_sample_book()

    def test_book_str_successfully(self):
        self.assertEqual(str(self.book1), "Sample_book1 by Author1 | soft cover | 11 pcs")


class AnonymousUserBookAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

        self.book1 = init_sample_book()
        self.book2 = init_sample_book(title="Sample_book2")

        self.payload = {
            "title": "Sample_book1",
            "author": "Author1",
            "cover": Book.CoverType.SOFT,
            "inventory": 2,
            "daily_fee": 10,
        }

    def test_anonymous_user_book_list(self):
        response = self.client.get(BOOK_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        books = Book.objects.all()
        serializer = BookSerializer(books, many=True)
        self.assertEqual(response.data.get("results"), serializer.data)

    def test_anonymous_user_book_post_unathorized(self):
        response = self.client.post(BOOK_URL, self.payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_user_book_detail(self):
        response = self.client.get(detail_url(BOOK_DETAIL_URL, self.book1.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        serializer = BookSerializer(response.data)
        self.assertEqual(response.data, serializer.data)

    def test_anonymous_user_book_put_unathorized(self):
        response = self.client.put(detail_url(BOOK_DETAIL_URL, self.book1.pk), self.payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class NonAdminUserBookAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = init_sample_user(1)
        self.client.force_authenticate(self.user1)

        self.book1 = init_sample_book()
        self.book2 = init_sample_book(title="Sample_book2")

        self.payload = {
            "title": "Sample_book1",
            "author": "Author1",
            "cover": Book.CoverType.SOFT,
            "inventory": 2,
            "daily_fee": 10,
        }

    def test_non_admin_user_book_list(self):
        response = self.client.get(BOOK_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        books = Book.objects.all()
        serializer = BookSerializer(books, many=True)
        self.assertEqual(response.data.get("results"), serializer.data)

    def test_non_admin_user_book_post_forbidden(self):
        response = self.client.post(BOOK_URL, self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_admin_user_book_detail(self):
        response = self.client.get(detail_url(BOOK_DETAIL_URL, self.book1.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        serializer = BookSerializer(response.data)
        self.assertEqual(response.data, serializer.data)

    def test_non_admin_user_book_put_forbidden(self):
        response = self.client.put(detail_url(BOOK_DETAIL_URL, self.book1.pk), self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminUserBooksAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = init_sample_admin_user(1)
        self.client.force_authenticate(self.user1)

        self.book1 = init_sample_book()
        self.book2 = init_sample_book(title="Sample_book2")

        self.payload = {
            "title": "Sample_book3",
            "author": "Author3",
            "cover": Book.CoverType.HARD,
            "inventory": 3,
            "daily_fee": 5.12,
        }

    def test_admin_user_book_post(self):
        response = self.client.post(BOOK_URL, self.payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        id = response.data.get("id")
        serializer = BookSerializer(Book.objects.get(pk=id))
        self.assertEqual(response.data, serializer.data)

    def test_admin_user_book_put(self):
        response = self.client.put(detail_url(BOOK_DETAIL_URL, self.book1.pk), self.payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        id = response.data.get("id")
        serializer = BookSerializer(Book.objects.get(pk=id))
        self.assertEqual(response.data, serializer.data)

    def test_admin_user_book_delete(self):
        book_count = Book.objects.count()
        response = self.client.delete(detail_url(BOOK_DETAIL_URL, self.book1.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Book.objects.count(), book_count - 1)
