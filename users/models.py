from django.db import models
from django.utils.translation import gettext as _

from django.contrib.auth.models import AbstractUser

from users.managers import UserManager


class User(AbstractUser):
    username = None
    email = models.EmailField(_("email address"), unique=True, db_index=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.email
