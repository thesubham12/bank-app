from django.db import models
from app2.models import SavingsAccount


class TransactionHistory(models.Model):

    TRANSACTION_TYPES = [
        ('deposit',           'Deposit'),
        ('withdraw',          'Withdraw'),
        ('transfer_sent',     'Transfer Sent'),
        ('transfer_received', 'Transfer Received'),
    ]

    account = models.ForeignKey(
        SavingsAccount,
        on_delete=models.CASCADE,
        related_name='transactions'
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    balance_after = models.DecimalField(max_digits=12, decimal_places=2)

    related_account_number = models.CharField(max_length=20, blank=True, null=True)
    related_account_name   = models.CharField(max_length=100, blank=True, null=True)

    remark = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} ₹{self.amount} — {self.account.full_name}"