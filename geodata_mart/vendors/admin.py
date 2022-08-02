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
        "logo",
        "media",
        "users",
        "staff",
        "admins",
    ]


@admin.register(models.VendorMessage)
class VendorMessageAdmin(admin.ModelAdmin):
    """Messages"""

    list_display = (
        "id",
        "sender",
        "receiver",
        "subject",
        "category",
        "preview",
        "project",
        "job",
        "parent",
        "created_date",
    )
    list_display_links = ("id",)
    list_filter = (
        "sender",
        "receiver",
        "category",
        "project",
    )
    search_fields = ("sender", "receiver", "content")
    ordering = ("-created_date", "id", "receiver", "sender")
    fields = [
        "sender",
        "receiver",
        "subject",
        "category",
        "content",
        "project",
        "job",
        "parent",
    ]
