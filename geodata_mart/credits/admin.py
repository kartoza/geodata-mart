from django.contrib import admin
from geodata_mart.credits import models


@admin.register(models.Account)
class CreditAccountAdmin(admin.ModelAdmin):
    """Account Balances"""

    list_display = (
        "id",
        "account_name",
        "account_balance",
        "created_date",
        "updated_date",
        "account_owner",
        "is_organizational",
        "account_organization",
        "created_date",
        "updated_date",
    )
    list_display_links = ("id", "account_name")
    list_filter = (
        "account_name",
        "account_owner",
        "is_organizational",
        "account_organization",
    )
    search_fields = ("account_name", "account_owner", "id")
    ordering = ("-updated_date", "account_balance", "account_owner")
    fields = [
        "account_name",
        "account_balance",
        "account_owner",
        "is_organizational",
    ]

    @admin.display(
        boolean=True,
    )
    def is_organizational(self, obj):
        """Modify is_organizational to display as on/ off boolean icon"""
        return obj.is_organizational


@admin.register(models.Transaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    """Account Transactions"""

    list_display = (
        "id",
        "account",
        "value",
        "metadata",
        "state",
        "created_date",
        "updated_date",
    )
    list_display_links = ("id",)
    list_filter = (
        "account",
        "value",
        "state",
    )
