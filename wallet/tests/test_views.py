import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from wallet.models import Wallet, Transaction


@pytest.fixture
def api_client():
    """Create an API client that can be reused across tests."""
    return APIClient()


@pytest.fixture
def test_wallet():
    """Create a fresh wallet for each test."""
    wallet = Wallet.objects.create(label="Test Wallet")
    return wallet


@pytest.fixture
def wallet_with_transactions():
    """Create a wallet with predefined transactions."""
    wallet = Wallet.objects.create(label="Wallet with Transactions")
    Transaction.objects.create(wallet=wallet, txid="test-tx1", amount=Decimal("100"))
    Transaction.objects.create(wallet=wallet, txid="test-tx2", amount=Decimal("50"))
    Transaction.objects.create(wallet=wallet, txid="test-tx3", amount=Decimal("-30"))
    return wallet


@pytest.mark.django_db
class TestWalletViewSet:
    @pytest.mark.parametrize(
        "wallet_data,expected_status",
        [
            ({"label": "Valid Wallet"}, status.HTTP_201_CREATED),
            ({"label": ""}, status.HTTP_400_BAD_REQUEST),  # Empty label
            ({}, status.HTTP_400_BAD_REQUEST),  # Missing label
        ],
    )
    def test_create_wallet(self, api_client, wallet_data, expected_status):
        """Test creating a wallet through the API with different inputs."""
        url = reverse("wallet-list")
        response = api_client.post(url, wallet_data, format="json")

        assert response.status_code == expected_status

        if expected_status == status.HTTP_201_CREATED:
            assert response.data["label"] == wallet_data["label"]
            assert response.data["balance"] == "0.000000000000000000"
            assert "id" in response.data
            assert Wallet.objects.filter(id=response.data["id"]).exists()

    def test_list_wallets(self, api_client):
        """Test listing wallets through the API."""
        Wallet.objects.create(label="Wallet 1")
        Wallet.objects.create(label="Wallet 2")

        url = reverse("wallet-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        assert len(response.data["results"]) == 2

        # Check that the wallets are returned in the expected order (newest first)
        assert response.data["results"][0]["label"] == "Wallet 2"
        assert response.data["results"][1]["label"] == "Wallet 1"

    def test_retrieve_wallet(self, api_client, test_wallet):
        """Test retrieving a single wallet through the API."""
        url = reverse("wallet-detail", args=[test_wallet.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == test_wallet.id
        assert response.data["label"] == test_wallet.label
        assert "recent_transactions" in response.data

    @pytest.mark.parametrize(
        "update_data,expected_status,expected_label",
        [
            ({"label": "New Label"}, status.HTTP_200_OK, "New Label"),
            ({"label": ""}, status.HTTP_400_BAD_REQUEST, "Old Label"),  # Empty label
            ({}, status.HTTP_200_OK, "Old Label"),  # No change
        ],
    )
    def test_update_wallet(self, api_client, update_data, expected_status, expected_label):
        """Test updating a wallet through the API with different inputs."""
        wallet = Wallet.objects.create(label="Old Label")
        url = reverse("wallet-detail", args=[wallet.id])

        response = api_client.patch(url, update_data, format="json")
        assert response.status_code == expected_status

        # Verify the change (or lack of change) in the database
        wallet.refresh_from_db()
        assert wallet.label == expected_label

    def test_wallet_transactions_endpoint(self, api_client, wallet_with_transactions):
        """Test the custom endpoint for retrieving a wallet's transactions."""
        url = reverse("wallet-transactions", args=[wallet_with_transactions.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3
        assert len(response.data["results"]) == 3

        # Transactions should be returned newest first
        assert response.data["results"][0]["txid"] == "test-tx3"
        assert response.data["results"][1]["txid"] == "test-tx2"
        assert response.data["results"][2]["txid"] == "test-tx1"

    @pytest.mark.parametrize(
        "query_params,expected_count,expected_labels",
        [
            ("?label=Test Wallet", 1, ["Test Wallet"]),   # Filter by exact label
            ("?search=wallet", 2, ["Test Wallet", "Another Wallet"]),   # Search for partial match
            ("", 3, ["Test Wallet", "Another Wallet", "Something Else"]),  # No filter should return all
        ],
    )
    def test_wallet_filter_and_search(self, api_client, query_params, expected_count, expected_labels):
        """Test filtering and searching wallets with different query parameters."""
        Wallet.objects.create(label="Test Wallet")
        Wallet.objects.create(label="Another Wallet")
        Wallet.objects.create(label="Something Else")

        url = reverse("wallet-list") + query_params
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == expected_count

        # Verify the expected labels are in the response
        result_labels = [wallet["label"] for wallet in response.data["results"]]
        for expected_label in expected_labels:
            assert expected_label in result_labels


@pytest.mark.django_db
class TestTransactionViewSet:
    @pytest.mark.parametrize(
        "transaction_data,expected_status",
        [
            ({"amount": "50.123456789012345678"}, status.HTTP_201_CREATED),  # Valid transaction
            ({"amount": "-50"}, status.HTTP_400_BAD_REQUEST),  # Invalid: negative amount when wallet has zero balance
            ({}, status.HTTP_400_BAD_REQUEST),  # Invalid: missing amount
        ],
    )
    def test_create_transaction(self, api_client, test_wallet, transaction_data, expected_status):
        """Test creating transactions with different inputs."""
        transaction_data["wallet"] = test_wallet.id
        url = reverse("transaction-list")

        response = api_client.post(url, transaction_data, format="json")
        assert response.status_code == expected_status

        if expected_status == status.HTTP_201_CREATED:
            assert response.data["wallet"] == test_wallet.id
            assert "txid" in response.data
            assert response.data["amount"] == transaction_data["amount"]

            # Verify transaction exists and wallet balance was updated
            assert Transaction.objects.filter(id=response.data["id"]).exists()
            test_wallet.refresh_from_db()
            assert test_wallet.balance == Decimal(transaction_data["amount"])

    def test_list_transactions(self, api_client, wallet_with_transactions):
        """Test listing transactions through the API."""
        url = reverse("transaction-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3
        assert len(response.data["results"]) == 3

    def test_retrieve_transaction(self, api_client, wallet_with_transactions):
        """Test retrieving a single transaction through the API."""
        tx = Transaction.objects.filter(wallet=wallet_with_transactions).first()

        url = reverse("transaction-detail", args=[tx.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tx.id
        assert response.data["txid"] == tx.txid
        assert response.data["amount"] == str(tx.amount) + "0" * (18 - len(str(tx.amount).split(".")[-1]))

    @pytest.mark.parametrize(
        "http_method,expected_status",
        [
            ("patch", status.HTTP_405_METHOD_NOT_ALLOWED),  # Test partial update
            ("put", status.HTTP_405_METHOD_NOT_ALLOWED),  # Test full update
            ("delete", status.HTTP_405_METHOD_NOT_ALLOWED),  # Test delete
        ],
    )
    def test_transaction_immutability(self, api_client, wallet_with_transactions, http_method, expected_status):
        """Test that transactions cannot be modified or deleted."""
        tx = Transaction.objects.filter(wallet=wallet_with_transactions).first()
        url = reverse("transaction-detail", args=[tx.id])

        # Store original amount for verification later
        original_amount = tx.amount

        # Use the http_method parameter to determine which request to make
        if http_method == "patch":
            response = api_client.patch(url, {"amount": "999"}, format="json")
        elif http_method == "put":
            response = api_client.put(url, {"wallet": tx.wallet.id, "amount": "999"}, format="json")
        elif http_method == "delete":
            response = api_client.delete(url)

        assert response.status_code == expected_status

        # Verify the transaction was not changed
        tx.refresh_from_db()
        assert tx.amount == original_amount
        assert Transaction.objects.filter(id=tx.id).exists()

    @pytest.mark.parametrize(
        "initial_balance,negative_amount,expected_status",
        [
            ("30", "-20", status.HTTP_201_CREATED),  # Valid: 30 - 20 = 10 > 0
            ("30", "-30", status.HTTP_201_CREATED),  # Valid boundary: 30 - 30 = 0
            ("30", "-50", status.HTTP_400_BAD_REQUEST),  # Invalid: 30 - 50 = -20 < 0
        ],
    )
    def test_transaction_negative_amount_validation(
            self, api_client, test_wallet, initial_balance, negative_amount, expected_status
    ):
        """Test validation for transactions with negative amounts that might make wallet balance negative."""
        if Decimal(initial_balance) > 0:
            Transaction.objects.create(
                wallet=test_wallet, amount=Decimal(initial_balance)
            )
            test_wallet.refresh_from_db()
            assert test_wallet.balance == Decimal(initial_balance)

        # Try to create a negative transaction
        url = reverse("transaction-list")
        data = {
            "wallet": test_wallet.id,
            "amount": negative_amount
        }

        response = api_client.post(url, data, format="json")
        assert response.status_code == expected_status

        # Verify wallet balance
        test_wallet.refresh_from_db()
        if expected_status == status.HTTP_201_CREATED:
            assert test_wallet.balance == Decimal(initial_balance) + Decimal(negative_amount)
        else:
            assert test_wallet.balance == Decimal(initial_balance)

    @pytest.mark.parametrize(
        "query_params,expected_count",
        [
            ("?wallet={wallet_id}", 3),  # Filter by wallet
            ("?search=test-tx2", 1),   # Search by txid
            ("", 3),  # No filter should return all
        ],
    )
    def test_transaction_filter_and_search(self, api_client, wallet_with_transactions, query_params, expected_count):
        """Test filtering and searching transactions with different query parameters."""
        # Format the query_params with the actual wallet ID if needed
        query_params = query_params.format(wallet_id=wallet_with_transactions.id)

        url = reverse("transaction-list") + query_params
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == expected_count
