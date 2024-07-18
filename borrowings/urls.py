from django.urls import path, include
from rest_framework import routers

from borrowings.views import BorrowingsViewSet

app_name = "borrowings"

router = routers.DefaultRouter()
router.register("", BorrowingsViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
