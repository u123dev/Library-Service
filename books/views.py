from django.shortcuts import render
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import viewsets

from books.models import Book
from books.permissions import IsAdminOrReadOnly
from books.serializers import BookSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List of all books",
    ),
    create=extend_schema(
        summary="Add new book",
    ),
    retrieve=extend_schema(
        summary="Get book object by id",
    ),
    update=extend_schema(
        summary="Update book",
    ),
    partial_update=extend_schema(
        summary="Partial update book",
        description="""Change some of book properties""",
    ),
    destroy=extend_schema(
        summary="Delete book",
    ),
)
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = (IsAdminOrReadOnly,)
