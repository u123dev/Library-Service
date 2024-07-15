from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from tests.init_sample import init_sample_user, init_sample_admin_user


class ModelUserTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = init_sample_user(1)
        # self.client.force_authenticate(self.user1)
        self.user2 = init_sample_admin_user(2)

    def test_user_created_successfully(self):
        self.assertEqual(self.user1.get_username(), "test-1@test.com")

    def test_admin_user_created_successfully(self):
        self.assertEqual(self.user2.get_username(), "test-2@test.com")

    def test_user_str_successfully(self):
        self.assertEqual(str(self.user1), "test-1@test.com")

    def test_user_full_name_successfully(self):
        self.assertEqual(self.user1.full_name, "test-1")


USER_CREATE_URL = reverse("users:create")


class ApiUserTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # self.user1 = init_sample_user(1)
        # self.client.force_authenticate(self.user1)

    def test_api_user_created_successfully(self):
        payload = {
            "email": "test-1@test.com",
            "password": "testpass",
        }

        response = self.client.post(USER_CREATE_URL, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data["email"], "test-1@test.com")

    def test_api_admin_user_created_successfully(self):
        payload = {
            "email": "test-1@test.com",
            "password": "testpass",
            "is_staff": True,
        }

        response = self.client.post(USER_CREATE_URL, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data["email"], "test-1@test.com")

    def test_api_user_not_created_with_bad_email(self):
        payload = {
            "email": "test@-1@test.com",
            "password": "testpass",
        }

        response = self.client.post(USER_CREATE_URL, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_api_user_not_created_with_no_email(self):
        payload = {
            "password": "testpass",
        }

        response = self.client.post(USER_CREATE_URL, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
