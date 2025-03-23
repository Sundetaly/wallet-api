import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from wallet.models import Wallet, Transaction


@pytest.fixture
def test_wallet():
    """Create a fresh wallet for each test."""
    wallet = Wallet.objects.create(label="Test Wallet")
    return wallet


@pytest.mark.django_db
class TestWalletModel:
    def test_wallet_creation(self):
        """Test creating a wallet with valid data."""
        wallet = Wallet.objects.create(label="Test Wallet")
        assert wallet.id is not None
        assert wallet.label == "Test Wallet"
        assert wallet.balance == Decimal("0")

    @pytest.mark.parametrize(
        "transactions,expected_balance",
        [
            # Single transaction test
            ([("tx1", "100.5")], Decimal("100.5")),
            # Multiple transactions test
            ([("tx1", "100.5"), ("tx2", "50.75")], Decimal("151.25")),
            # With negative transaction test
            ([("tx1", "100.5"), ("tx2", "50.75"), ("tx3", "-30")], Decimal("121.25")),
            # Zero sum test
            ([("tx1", "100"), ("tx2", "-100")], Decimal("0")),
        ],
    )
    def test_wallet_balance_update(self, test_wallet, transactions, expected_balance):
        """Test that wallet balance updates correctly with various transaction patterns."""
        for txid, amount in transactions:
            Transaction.objects.create(
                wallet=test_wallet, txid=txid, amount=Decimal(amount)
            )

        # Verify the final balance
        test_wallet.refresh_from_db()
        assert test_wallet.balance == expected_balance


@pytest.mark.django_db
class TestTransactionModel:
    def test_transaction_creation(self, test_wallet):
        """Test creating a transaction with valid data."""
        transaction = Transaction.objects.create(
            wallet=test_wallet, amount=Decimal("123.456789")
        )

        assert transaction.id is not None
        assert transaction.wallet == test_wallet
        assert transaction.txid is not None  # UUID should be auto-generated
        assert transaction.amount == Decimal("123.456789")

        # Check that the wallet balance was updated
        test_wallet.refresh_from_db()
        assert test_wallet.balance == Decimal("123.456789")

    @pytest.mark.parametrize(
        "initial_amount,transaction_amount,expected_balance",
        [
            ("200", "-50", "150"),  # Standard negative transaction
            ("100", "-100", "0"),   # Boundary case - exactly zero
            ("0", "50", "50"),      # Starting from zero
            ("200", "300", "500"),  # Positive transaction
        ],
    )
    def test_transaction_balance_calculations(
        self, test_wallet, initial_amount, transaction_amount, expected_balance
    ):
        """Test various transaction scenarios with different amounts."""
        if Decimal(initial_amount) > 0:
            Transaction.objects.create(
                wallet=test_wallet, amount=Decimal(initial_amount)
            )
            test_wallet.refresh_from_db()
            assert test_wallet.balance == Decimal(initial_amount)

        transaction = Transaction.objects.create(
            wallet=test_wallet, amount=Decimal(transaction_amount)
        )

        assert transaction.id is not None
        assert transaction.amount == Decimal(transaction_amount)

        # Check that the wallet balance was updated correctly
        test_wallet.refresh_from_db()
        assert test_wallet.balance == Decimal(expected_balance)

    def test_transaction_unique_txid(self, test_wallet):
        """Test that transaction txid is automatically generated and unique."""
        tx1 = Transaction.objects.create(
            wallet=test_wallet, amount=Decimal("100")
        )

        tx2 = Transaction.objects.create(
            wallet=test_wallet, amount=Decimal("200")
        )

        # Check that both transactions have different txids
        assert tx1.txid != tx2.txid

    @pytest.mark.parametrize(
        "initial_balance,negative_amount,should_raise",
        [
            ("50", "-40", False),    # Valid: 50 - 40 = 10 > 0
            ("50", "-50", False),    # Valid boundary: 50 - 50 = 0
            ("50", "-51", True),     # Invalid: 50 - 51 = -1 < 0
            ("50", "-100", True),    # Invalid: 50 - 100 = -50 < 0
            ("0", "-0.01", True),    # Invalid: 0 - 0.01 = -0.01 < 0
        ],
    )
    def test_transaction_negative_balance_validation(
        self, test_wallet, initial_balance, negative_amount, should_raise
    ):
        """Test validation for transactions that would make the wallet balance negative."""
        if Decimal(initial_balance) > 0:
            Transaction.objects.create(
                wallet=test_wallet, amount=Decimal(initial_balance)
            )
            test_wallet.refresh_from_db()
            assert test_wallet.balance == Decimal(initial_balance)

        if should_raise:
            with pytest.raises(ValidationError):
                Transaction.objects.create(
                    wallet=test_wallet, amount=Decimal(negative_amount)
                )
            # Verify wallet balance hasn't changed
            test_wallet.refresh_from_db()
            assert test_wallet.balance == Decimal(initial_balance)
        else:
            Transaction.objects.create(
                wallet=test_wallet, amount=Decimal(negative_amount)
            )
            # Verify wallet balance updated correctly
            test_wallet.refresh_from_db()
            assert test_wallet.balance == Decimal(initial_balance) + Decimal(negative_amount)