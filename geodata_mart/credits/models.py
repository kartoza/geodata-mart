from django.db import models
from django.contrib.postgres.fields import JSONField
from geodata_mart.vendors.models import Vendor
from django.utils.translation import gettext_lazy as _


class StateChoices(models.IntegerChoices):
    """Default state choices for transactions"""

    UNSPECIFIED = 0, _("Unspecified")
    PROCESSED = 1, _("Processed")
    PENDING = 2, _("Pending")
    UNPROCESSED = 3, _("Unprocessed")
    REVERSED = 4, _("Reversed")
    CANCELLED = 5, _("Cancelled")
    ARCHIVED = 6, _("Archived")
    REMOVED = 7, _("Removed")
    ERROR = 8, _("Error")
    OTHER = 9, _("Other")


class Account(models.Model):
    account_name = models.CharField(
        _("Account Name"), max_length=255, default="Primary", blank=True, null=True
    )
    account_balance = models.FloatField(
        _("Balance"), default=0, blank=False, null=False
    )
    created_date = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Created Date")
    )
    updated_date = models.DateTimeField(auto_now=True, verbose_name=_("Updated Date"))
    account_owner = models.ForeignKey(
        "users.User",
        on_delete=models.DO_NOTHING,
        verbose_name=_("Account Owner"),
        null=False,
        blank=False,
    )
    is_organizational = models.BooleanField(
        _("Organizational Account"),
        max_length=255,
        default=False,
        blank=True,
        null=True,
    )
    account_organization = models.ForeignKey(
        Vendor,
        on_delete=models.DO_NOTHING,
        verbose_name=_("Organization"),
        null=True,
        blank=True,
    )


# Should log debits and credits for double entry auditing
class Transaction(models.Model):
    """Log transactions for consuming or loading credits."""

    account = models.ForeignKey(
        Account, on_delete=models.DO_NOTHING, blank=False, null=False, unique=False
    )
    metadata = models.JSONField(_("Transaction Metadata"))
    value = models.FloatField(
        _("Transaction Value"), default=0, blank=False, null=False
    )
    state = models.IntegerField(
        choices=StateChoices.choices, default=StateChoices.UNSPECIFIED
    )
    created_date = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Created Date")
    )
    updated_date = models.DateTimeField(auto_now=True, verbose_name=_("Updated Date"))
