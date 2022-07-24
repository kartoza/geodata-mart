from django.db import models
from django.utils.translation import gettext_lazy as _
from geodata_mart.users.models import User

import uuid


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

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    def preview(self):
        return self.description[:100]


class VendorMessage(models.Model):
    """
    Messages for users to provide feedback to vendors.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        blank=False,
        null=False,
    )
    sender = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="sender")
    receiver = models.ForeignKey(
        Vendor, on_delete=models.CASCADE, related_name="receiver"
    )
    content = models.TextField(verbose_name=_("Message"), blank=True, null=True)
    subject = models.CharField(_("Subject"), max_length=255, blank=True, null=True)
    category = models.CharField(_("Category"), max_length=255, blank=True, null=True)
    project = models.ForeignKey(
        "maps.Project", on_delete=models.DO_NOTHING, blank=True, null=True
    )
    job = models.ForeignKey(
        "maps.Job", on_delete=models.DO_NOTHING, blank=True, null=True
    )
    parent = models.ForeignKey(
        "self", on_delete=models.DO_NOTHING, blank=True, null=True
    )
    created_date = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Created Date")
    )

    def __str__(self):
        return str(self.id)

    def __unicode__(self):
        return str(self.id)

    def preview(self):
        return self.content[:100]
