from django.contrib import admin
from geodata_mart.vendors import models


@admin.register(models.Vendor)
class VendorAdmin(admin.ModelAdmin):
    """Data vendors"""

    list_display = (
        "id",
        "name",
        "abstract",
        "description",
        "users",
        "staff",
        "admins",
        "created_date",
        "updated_date",
    )
    list_display_links = ("id", "name")
    list_filter = (
        "name",
        "users",
        "staff",
        "admins",
    )
    search_fields = ("name", "abstract", "description")
    ordering = ("-updated_date", "id", "name")
    fields = [
        "name",
        "abstract",
        "description",
        "users",
        "staff",
        "admins",
    ]
