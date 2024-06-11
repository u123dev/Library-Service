from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from borrowings.models import Borrowing
from borrowings.serializers import BorrowingSerializer, BorrowingCreateSerializer


class BorrowingsViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    # serializer_class = BorrowingSerializer
    permission_classes = (IsAuthenticated, )

    def get_serializer_class(self):
        if self.action in ("create", "update", ):
            return BorrowingCreateSerializer
        return BorrowingSerializer
