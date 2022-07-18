from django.db import models


class DevAppExample(models.Model):
    """DevApp example model for testing and development"""

    short_name = models.CharField("Short Name", max_length=20)
    full_name = models.CharField("Full Name", max_length=255)
    abstract = models.TextField(
        verbose_name="Test Item Abstract", blank=True, null=True
    )
    created_date = models.DateTimeField(auto_now_add=True, verbose_name="Created Date")
    updated_date = models.DateTimeField(auto_now=True, verbose_name="Updated Date")

    class Meta:
        verbose_name = "Test Item"
        verbose_name_plural = "Test Items"

    def __str__(self):
        return self.short_name

    def __unicode__(self):
        return self.short_name

    def preview(self):
        return self.abstract[:100]
