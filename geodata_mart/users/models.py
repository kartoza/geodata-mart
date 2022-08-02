from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from geodata_mart.credits.models import Account

from versatileimagefield.fields import VersatileImageField
from PIL import Image

from django.core.files.storage import FileSystemStorage
from django.conf import settings

project_storage = FileSystemStorage(
    location=settings.QGIS_DATA_ROOT, base_url="/geodata/assets"
)


class User(AbstractUser):
    """
    Default custom user model for Geodata Mart.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    def getUserUploadPath(instance, filename):
        """Get the users upload path as a callable

        Return the upload path using the current instance detail.

        Returns:
            string: path to output file for image field
        """
        # return f"media/users/{instance.user.user.name}/{filename}"
        return f"media/users/{instance.user.user.id}/{filename}"

    #: First and last name do not cover name patterns around the globe
    name = models.CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore
    last_name = None  # type: ignore
    status = models.CharField(_("User Status"), blank=True, max_length=255)
    bio = models.CharField(_("User Bio"), blank=True, max_length=255)
    detail = models.TextField(verbose_name=_("User Detail"), blank=True, null=True)
    active_account = models.OneToOneField(
        "credits.Account",
        blank=True,
        null=True,
        related_name="active_user",
        on_delete=models.DO_NOTHING,
    )
    avatar = VersatileImageField(
        _("Avatar"),
        storage=project_storage,
        upload_to=getUserUploadPath,
        blank=True,
        null=True,
    )

    def get_absolute_url(self):
        """Get url for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})


@receiver(post_save, sender=User)
def createCreditAccount(sender, instance, **kwargs):
    """Create a default credit account for new users"""
    record_instance = sender.objects.get(pk=instance.pk)
    account_exists = Account.objects.filter(account_owner=record_instance)
    obj, created = Account.objects.get_or_create(
        account_owner=record_instance,
        defaults={"account_name": "Default"},
    )
    if not account_exists:
        record_instance.active_account = obj
        record_instance.save()


@receiver(post_save, sender=User)
def resize_avatar(sender, instance, **kwargs):
    """Resize the provided image to a maximum size of 600x600"""
    try:
        record_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if not record_instance.avatar or not project_storage.exists(
        record_instance.avatar.path
    ):
        return

    size = (600, 600)
    image = Image.open(record_instance.avatar.path)
    if image.size[0] > size[0] or image.size[1] > size[1]:
        image.thumbnail(size, resample=Image.Resampling.BICUBIC)
        image.save(record_instance.media.path)
