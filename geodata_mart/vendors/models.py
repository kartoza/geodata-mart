from django.db import models
from django.utils.translation import gettext_lazy as _
from geodata_mart.users.models import User


class Vendor(models.Model):
    """
    Model for data vendors on Geodata Mart.
    """

    name = models.CharField(
        _("Vendor Name"), unique=True, blank=False, null=False, max_length=255
    )
    abstract = models.CharField(
        _("Vendor Abstract"), blank=True, null=True, max_length=255
    )
    description = models.TextField(
        verbose_name="Vendor Description", blank=True, null=True
    )
    # image = models.ImageField(upload_to=getImageUploadPath, blank=True, null=True)
    created_date = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Created Date")
    )
    updated_date = models.DateTimeField(auto_now=True, verbose_name=_("Updated Date"))
    users = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("Users"),
        null=True,
        blank=True,
        related_name="users",
    )
    staff = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("Employees"),
        null=True,
        blank=True,
        related_name="staff",
    )
    admins = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("Administrators"),
        null=True,
        blank=True,
        related_name="admins",
    )
