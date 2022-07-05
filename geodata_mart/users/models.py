from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Default custom user model for Geodata Mart.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    #: First and last name do not cover name patterns around the globe
    name = models.CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore
    last_name = None  # type: ignore
    name = models.CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore
    last_name = None  # type: ignore
    # avatar = models.ImageField(upload_to=getAvatarUploadPath, blank=True, null=True)
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

    def get_absolute_url(self):
        """Get url for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})
