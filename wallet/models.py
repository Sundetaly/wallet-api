import uuid
from django.db import models
from django.db import transaction
from django.db.models import Sum
from django.core.exceptions import ValidationError


class Wallet(models.Model):
    """
    Wallet model to store user wallets.
    The balance is calculated based on the sum of all associated transactions.
    """

    label = models.CharField(max_length=255)
    # Balance field is calculated and should not be modified directly
    balance = models.DecimalField(
        max_digits=28, decimal_places=18, default=0, editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wallets"
        indexes = [
            models.Index(fields=["label"], name="wallet_label_idx"),
        ]

    def __str__(self):
        return f"{self.label} ({self.balance})"

    def update_balance(self):
        """Update the wallet balance based on all associated transactions."""
        total_amount = self.transactions.aggregate(Sum("amount"))["amount__sum"] or 0
        self.balance = total_amount
        self.save(update_fields=["balance", "updated_at"])
        return self.balance


class Transaction(models.Model):
    """
    Transaction model to store wallet transactions.
    Each transaction has a unique txid and an amount that can be positive or negative.
    The wallet's balance should never be negative after a transaction.
    """

    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name="transactions"
    )
    txid = models.CharField(
        max_length=255, unique=True, default=uuid.uuid4, editable=False
    )
    amount = models.DecimalField(max_digits=28, decimal_places=18)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transactions"
        indexes = [
            models.Index(fields=["txid"], name="tx_txid_idx"),
            models.Index(fields=["wallet"], name="tx_wallet_idx"),
            models.Index(fields=["created_at"], name="tx_created_at_idx"),
        ]

    def __str__(self):
        return f"{self.txid} ({self.amount})"

    def clean(self):
        """
        Ensure the transaction won't make the wallet balance negative.
        """
        if self.amount < 0 and self.wallet.balance + self.amount < 0:
            raise ValidationError(
                "This transaction would make the wallet balance negative, which is not allowed."
            )
        super().clean()

    def save(self, *args, **kwargs):
        # Use atomic transaction to ensure consistency
        with transaction.atomic():
            self.clean()
            super().save(*args, **kwargs)
            self.wallet.update_balance()
