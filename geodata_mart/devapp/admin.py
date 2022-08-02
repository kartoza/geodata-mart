from django.contrib import admin
from geodata_mart.devapp import models


@admin.register(models.DevAppExample)
class VendorAdmin(admin.ModelAdmin):
    """Data1 vendors"""

    list_display = (
        "id",
        "short_name",
        "full_name",
        "abstract",
        "created_date",
        "updated_date",
    )
    list_display_links = ("id", "short_name")
    list_filter = (
        "short_name",
        "full_name",
        "abstract",
        "created_date",
        "updated_date",
    )
    search_fields = ("short_name", "full_name", "abstract")
    ordering = ("-updated_date", "id", "short_name")
    fields = ["file_upload", "short_name", "full_name", "abstract"]
