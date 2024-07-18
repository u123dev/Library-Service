from django.urls import include, path
from rest_framework import routers

from payments.views import PaymentsViewSet


app_name = "payments"

router = routers.DefaultRouter()
router.register("", PaymentsViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
