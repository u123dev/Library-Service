from django.shortcuts import render
from rest_framework import viewsets

from borrowings.models import Borrowing
from borrowings.serializers import BorrowingSerializer


class BorrowingsViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    serializer_class = BorrowingSerializer
