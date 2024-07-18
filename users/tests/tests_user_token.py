from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from tests.init_sample import init_sample_user


USER_TOKEN_URL = reverse("users:token_obtain_pair")
USER_TOKEN_REFRESH_URL = reverse("users:token_refresh")
USER_TOKEN_VERIFY_URL = reverse("users:token_verify")


class TokenApiUserTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = init_sample_user(1)
        self.client.force_authenticate(self.user1)

    def test_user_get_token(self):
        payload = {
            "email": "test-1@test.com",
            "password": "testpass",
        }

        response = self.client.post(USER_TOKEN_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unregistered_user_get_token_unathorized(self):
        payload = {
            "email": "bad-test-1@test.com",
            "password": "bad-testpass",
        }

        response = self.client.post(USER_TOKEN_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_refresh_token(self):
        refresh_token = str(RefreshToken.for_user(self.user1))
        payload = {
            "refresh": refresh_token,
        }
        response = self.client.post(USER_TOKEN_REFRESH_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_verify_token(self):
        token = str(AccessToken.for_user(self.user1))
        payload = {
            "token": token,
        }
        response = self.client.post(USER_TOKEN_VERIFY_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_verify_bad_token(self):
        payload = {
            "token": "123",
        }
        response = self.client.post(USER_TOKEN_VERIFY_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
