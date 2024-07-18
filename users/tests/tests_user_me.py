from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from tests.init_sample import init_sample_user


USER_ME_URL = reverse("users:manage")


class AnonymousApiUserMeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # self.user1 = init_sample_user(1)
        # self.client.force_authenticate(self.user1)

    def test_anonymous_user_me_unathorized(self):
        response = self.client.get(USER_ME_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ApiUserMeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = init_sample_user(1)
        self.client.force_authenticate(self.user1)

    def test_user_me(self):
        response = self.client.get(USER_ME_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_me_update(self):
        payload = {
            "email": "new-test-1@test.com",
            "password": "new-testpass",
        }

        response = self.client.put(USER_ME_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "new-test-1@test.com")
