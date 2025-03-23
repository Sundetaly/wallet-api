from rest_framework import serializers
from .models import Wallet, Transaction


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for Transaction model.
    Validates that the transaction does not make wallet balance negative.
    """

    class Meta:
        model = Transaction
        fields = ["id", "wallet", "txid", "amount", "created_at"]
        read_only_fields = ["id", "txid", "created_at"]

    def validate(self, data):
        """
        Additional validation to ensure wallet balance doesn't go negative.
        """
        amount = data["amount"]
        wallet = data["wallet"]

        if amount < 0:
            # Check if this transaction would make the wallet balance negative
            if wallet.balance + amount < 0:
                raise serializers.ValidationError(
                    "This transaction would make the wallet balance negative, which is not allowed."
                )
        return data

    def create(self, validated_data):
        """
        Create a new transaction.
        The wallet balance will be updated in the Transaction.save() method.
        """
        transaction = Transaction.objects.create(**validated_data)
        return transaction


class WalletSerializer(serializers.ModelSerializer):
    """
    Serializer for Wallet model.
    """

    transactions_count = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = [
            "id",
            "label",
            "balance",
            "transactions_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "balance", "created_at", "updated_at"]

    def get_transactions_count(self, obj):
        """Get the count of transactions for this wallet."""
        return obj.transactions.count()


class WalletDetailSerializer(WalletSerializer):
    """
    Detailed Wallet serializer that includes recent transactions.
    """

    recent_transactions = serializers.SerializerMethodField()

    class Meta(WalletSerializer.Meta):
        fields = WalletSerializer.Meta.fields + ["recent_transactions"]

    def get_recent_transactions(self, obj):
        """Get the 10 most recent transactions for this wallet."""
        recent_txs = obj.transactions.order_by("-created_at")[:10]
        return TransactionSerializer(recent_txs, many=True).data
