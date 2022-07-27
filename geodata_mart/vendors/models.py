from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from django.utils.translation import gettext_lazy as _

import uuid
from versatileimagefield.fields import VersatileImageField
from PIL import Image

from django.core.files.storage import FileSystemStorage
from django.conf import settings

project_storage = FileSystemStorage(
    location=settings.QGIS_DATA_ROOT, base_url="/geodata/assets"
)


class Vendor(models.Model):
    """
    Model for data vendors on Geodata Mart.
    """

    def getVendorUploadPath(instance, filename):
        """Get the vendor media upload path as a callable

        Return the upload path using the current instance detail.

        Returns:
            string: path to output file for image field
        """
        return f"media/vendor/{instance.id}/{filename}"

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
        "users.User",
        on_delete=models.CASCADE,
        verbose_name=_("Users"),
        null=True,
        blank=True,
        related_name="users",
    )
    staff = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        verbose_name=_("Employees"),
        null=True,
        blank=True,
        related_name="staff",
    )
    admins = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        verbose_name=_("Administrators"),
        null=True,
        blank=True,
        related_name="admins",
    )
    logo = VersatileImageField(
        _("Logo"),
        storage=project_storage,
        upload_to=getVendorUploadPath,
        blank=True,
        null=True,
    )
    media = VersatileImageField(
        _("Media"),
        storage=project_storage,
        upload_to=getVendorUploadPath,
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    def preview(self):
        return self.description[:100]


@receiver(post_save, sender=Vendor)
def resize_logo(sender, instance, **kwargs):
    """Resize the provided image to a maximum size of 600x600"""
    try:
        record_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if not record_instance.logo or not project_storage.exists(
        record_instance.logo.path
    ):
        return

    size = (600, 600)
    logo_image = Image.open(record_instance.logo.path)
    if logo_image.size[0] > size[0] or logo_image.size[1] > size[1]:
        logo_image.thumbnail(size, resample=Image.Resampling.BICUBIC)
        logo_image.save(record_instance.media.path)


@receiver(post_save, sender=Vendor)
def resize_media(sender, instance, **kwargs):
    """Resize the provided image to a maximum size of 1200x1200"""
    try:
        record_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if not record_instance.media or not project_storage.exists(
        record_instance.media.path
    ):
        return

    media_size = (1200, 1200)
    media_image = Image.open(record_instance.media.path)
    if media_image.size[0] > size[0] or media_image.size[1] > size[1]:
        media_image.thumbnail(size, resample=Image.Resampling.BICUBIC)
        media_image.save(record_instance.media.path)


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
    sender = models.ForeignKey(
        "users.User", on_delete=models.DO_NOTHING, related_name="sender"
    )
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
