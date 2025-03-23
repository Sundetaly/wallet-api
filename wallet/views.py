from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from .models import Wallet, Transaction
from .serializers import (
    WalletSerializer,
    WalletDetailSerializer,
    TransactionSerializer,
)


class StandardResultsSetPagination(PageNumberPagination):
    """
    Custom pagination class for consistent pagination across all views.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class WalletViewSet(viewsets.ModelViewSet):
    """
    API endpoint for wallets.

    list:
        Get a paginated list of all wallets.
        Supports filtering, searching, and ordering.

    create:
        Create a new wallet.

    retrieve:
        Get details of a specific wallet, including recent transactions.

    update:
        Update all fields of a wallet.

    partial_update:
        Update select fields of a wallet.

    destroy:
        Delete a wallet.
    """

    queryset = Wallet.objects.all().order_by("-created_at")
    serializer_class = WalletSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["label"]
    search_fields = ["label"]
    ordering_fields = ["label", "balance", "created_at", "updated_at"]

    def get_serializer_class(self):
        """Return the appropriate serializer based on the action."""
        if self.action == "retrieve":
            return WalletDetailSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=["get"])
    def transactions(self, request, pk=None):
        """
        Get all transactions for a specific wallet with pagination.

        This endpoint retrieves a paginated list of all transactions
        associated with the specified wallet.
        """
        wallet = self.get_object()
        transactions = wallet.transactions.all().order_by("-created_at")

        # Apply pagination
        page = self.paginate_queryset(transactions)
        if page is not None:
            serializer = TransactionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)


class TransactionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for transactions.

    list:
        Get a paginated list of all transactions.
        Supports filtering, searching, and ordering.

    create:
        Create a new transaction.
        Transaction amount can be positive or negative, but a negative amount
        must not make the wallet balance negative.

    retrieve:
        Get details of a specific transaction.

    update:
        Not allowed. Transactions cannot be modified once created.

    partial_update:
        Not allowed. Transactions cannot be modified once created.

    destroy:
        Not allowed. Transactions cannot be deleted once created.
    """

    queryset = Transaction.objects.all().order_by("-created_at")
    serializer_class = TransactionSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["wallet", "txid"]
    search_fields = ["txid"]
    ordering_fields = ["amount", "created_at"]

    def update(self, request, *args, **kwargs):
        """
        Disable update operation for transactions.
        """
        return Response(
            {"detail": "Updating transactions is not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        """
        Disable partial update operation for transactions.
        """
        return Response(
            {"detail": "Updating transactions is not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        """
        Disable delete operation for transactions.
        """
        return Response(
            {"detail": "Deleting transactions is not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
