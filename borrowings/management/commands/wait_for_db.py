import time
from django.db import connections
from django.db.utils import OperationalError
from django.core.management import BaseCommand

from library_service.settings import DATABASES


class Command(BaseCommand):
    """Django command to pause execution until db is available"""

    def handle(self, *args, **options):
        self.stdout.write(f"Waiting for database... {DATABASES["default"]["NAME"]}")
        db_conn = None
        while not db_conn:
            try:
                db_conn = connections["default"].cursor()
            except OperationalError:
                self.stdout.write("Database unavailable, waititng 1 second...")
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS("Database available!"))
