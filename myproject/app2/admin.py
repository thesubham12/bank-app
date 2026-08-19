from django.contrib import admin
from .models import SavingsAccount


@admin.register(SavingsAccount)
class SavingsAccountAdmin(admin.ModelAdmin):

    list_display = (
        'customer_id',
        'full_name',
        'account_number',
        'mobile_number',
        'balance',
        'created_at'
    )

    search_fields = (
        'customer_id',
        'full_name',
        'account_number',
        'mobile_number'
    )

    list_filter = (
        'created_at',
    )