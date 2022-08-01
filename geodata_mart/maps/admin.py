from django.contrib import admin
from django.contrib import messages
from geodata_mart.maps import models


@admin.register(models.MetaTags)
class MetaTagsAdmin(admin.ModelAdmin):
    """Manage metadata tags."""

    list_display = (
        "id",
        "short_name",
        "full_name",
        "abstract",
        "description",
        "comment",
    )
    list_display_links = ("id", "short_name")
    list_filter = ("short_name",)
    search_fields = ("short_name", "abstract", "description", "comment")
    ordering = ("id",)
    fields = [
        "short_name",
        "full_name",
        "abstract",
        "description",
        "comment",
    ]


@admin.register(models.SpatialReferenceSystem)
class SpatialReferenceSystemAdmin(admin.ModelAdmin):
    """Manage spatial reference system definitions tags."""

    list_display = (
        "id",
        "short_name",
        "idstring",
        "full_name",
        "abstract",
        "description",
        "comment",
    )
    list_display_links = ("id", "short_name", "idstring")
    list_filter = ("short_name", "idstring")
    search_fields = ("short_name", "idstring", "abstract", "description", "comment")
    ordering = ("id", "idstring")
    fields = [
        "short_name",
        "idstring",
        "full_name",
        "abstract",
        "description",
        "proj",
        "wkt",
        "type",
        "comment",
    ]


@admin.register(models.ResultFile)
class ResultFileAdmin(admin.ModelAdmin):
    """Upload, review, manage, and process Result Files"""

    list_display = (
        "id",
        "file_name",
        "file_object",
        "version",
        "comment",
        "file_size",
        "file_stored",
        "created_date",
        "updated_date",
    )
    list_display_links = ("id", "file_name")
    list_filter = ("file_name", "created_date", "updated_date")
    search_fields = ("file_name", "comment")
    ordering = ("-updated_date",)
    fields = [
        "file_name",
        "file_object",
        "version",
        "comment",
    ]
    actions = [
        "set_state_0",
        "set_state_1",
        "set_state_2",
        "set_state_3",
        "set_state_4",
        "set_state_5",
        "set_state_6",
        "set_state_7",
        "set_state_8",
        "set_state_9",
        "remove_file_object",
    ]

    @admin.display(
        boolean=True,
    )
    def file_stored(self, obj):
        """Modify file_available to display as on/ off boolean icon

        Simply swapping 'file_stored' 'file_available' in list_display
        and removing this method and accompanying boolean=True statement
        will render the same result as text rather than a graphic"""
        return obj.file_available()

    @admin.action(description="Delete source file from filesystem")
    def remove_file_object(self, request, queryset):
        for instance in queryset:
            try:
                instance.remove_file()
            except Exception as e:
                self.message_user(request, e, level=messages.ERROR)

    @admin.action(description="Set selected file status to Unspecified")
    def set_state_0(self, request, queryset):
        queryset.update(state=0)

    @admin.action(description="Set selected file status to Processed")
    def set_state_1(self, request, queryset):
        queryset.update(state=1)

    @admin.action(description="Set selected file status to Active")
    def set_state_2(self, request, queryset):
        queryset.update(state=2)

    @admin.action(description="Set selected file status to Deactivated")
    def set_state_3(self, request, queryset):
        queryset.update(state=3)

    @admin.action(description="Set selected file status to Hidden")
    def set_state_4(self, request, queryset):
        queryset.update(state=4)

    @admin.action(description="Set selected file status to Deprecated")
    def set_state_5(self, request, queryset):
        queryset.update(state=5)

    @admin.action(description="Set selected file status to Archived")
    def set_state_6(self, request, queryset):
        queryset.update(state=6)

    @admin.action(description="Set selected file status to Removed")
    def set_state_7(self, request, queryset):
        queryset.update(state=7)

    @admin.action(description="Set selected file status to Error")
    def set_state_8(self, request, queryset):
        queryset.update(state=8)

    @admin.action(description="Set selected file status to Other")
    def set_state_9(self, request, queryset):
        queryset.update(state=9)


@admin.register(models.PgServiceFile)
class PgServiceFileAdmin(ResultFileAdmin, admin.ModelAdmin):
    pass


@admin.register(models.QgisIniFile)
class QgisIniFileAdmin(ResultFileAdmin, admin.ModelAdmin):
    pass


@admin.register(models.AuthDbFile)
class AuthDbFileAdmin(ResultFileAdmin, admin.ModelAdmin):
    fields = [
        "file_name",
        "file_object",
        "secret",
        "version",
        "comment",
    ]


@admin.register(models.ProcessingScriptFile)
class ProcessingScriptFileAdmin(ResultFileAdmin, admin.ModelAdmin):
    pass


@admin.register(models.ProcessingModelFile)
class ProcessingModelFileAdmin(ResultFileAdmin, admin.ModelAdmin):
    pass


@admin.register(models.QgisProjectFile)
class QgisProjectFileAdmin(ResultFileAdmin, admin.ModelAdmin):
    """Upload, review, manage, and process QGIS Project Files"""

    list_display = ResultFileAdmin.list_display + ("state",)
    list_filter = ResultFileAdmin.list_filter + ("state",)
    fields = ResultFileAdmin.fields + [
        "state",
    ]


@admin.register(models.Job)
class JobAdmin(admin.ModelAdmin):
    """Manage Jobs"""

    list_display = (
        "id",
        "job_id",
        "user_id",
        "project_id",
        "state",
        "parameters",
        "tasks",
        "comment",
        "created_date",
        "updated_date",
    )
    list_display_links = ("id", "job_id")
    list_filter = ("project_id", "user_id", "state", "created_date", "updated_date")
    search_fields = ("project_id", "user_id", "comment")
    ordering = ("-created_date",)
    fields = [
        "job_id",
        "user_id",
        "project_id",
        "state",
        "layers",
        "parameters",
        "tasks",
        "comment",
    ]
    actions = [
        "set_state_0",
        "set_state_1",
        "set_state_2",
        "set_state_3",
        "set_state_4",
        "set_state_5",
        "set_state_6",
        "set_state_7",
        "set_state_8",
        "set_state_9",
    ]

    @admin.action(description="Set selected file status to Unspecified")
    def set_state_0(self, request, queryset):
        queryset.update(state=0)

    @admin.action(description="Set selected file status to Abandoned")
    def set_state_1(self, request, queryset):
        queryset.update(state=1)

    @admin.action(description="Set selected file status to Unfulfilled")
    def set_state_2(self, request, queryset):
        queryset.update(state=2)

    @admin.action(description="Set selected file status to Processed")
    def set_state_3(self, request, queryset):
        queryset.update(state=3)

    @admin.action(description="Set selected file status to Completed")
    def set_state_4(self, request, queryset):
        queryset.update(state=4)

    @admin.action(description="Set selected file status to Failed")
    def set_state_5(self, request, queryset):
        queryset.update(state=5)

    @admin.action(description="Set selected file status to Processing")
    def set_state_6(self, request, queryset):
        queryset.update(state=6)

    @admin.action(description="Set selected file status to Unknown")
    def set_state_7(self, request, queryset):
        queryset.update(state=7)

    @admin.action(description="Set selected file status to Stale")
    def set_state_8(self, request, queryset):
        queryset.update(state=8)

    @admin.action(description="Set selected file status to Other")
    def set_state_9(self, request, queryset):
        queryset.update(state=9)


@admin.register(models.Layer)
class LayerAdmin(admin.ModelAdmin):
    """Manage and review project layers"""

    list_display = (
        "id",
        "project_id",
        "short_name",
        "state",
        "layer_name",
        "abstract",
        "is_default",
        "cost",
        "cost_modifier",
        "description",
        "lyr_group",
        "lyr_type",
        "lyr_class",
        "comment",
        "created_date",
        "updated_date",
    )
    list_display_links = ("id", "short_name")
    list_filter = ("project_id", "state", "short_name", "created_date", "updated_date")
    search_fields = (
        "project_id",
        "short_name",
        "layer_name",
        "abstract",
        "description",
        "lyr_group",
        "lyr_type",
        "lyr_class",
        "comment",
    )
    ordering = (
        "project_id",
        "-updated_date",
    )
    fields = [
        "project_id",
        "short_name",
        "layer_name",
        "state",
        "is_default",
        "cost",
        "cost_modifier",
        "lyr_group",
        "lyr_type",
        "lyr_class",
        "comment",
        "siblings",
        "tags",
    ]
    actions = [
        "set_state_0",
        "set_state_1",
        "set_state_2",
        "set_state_3",
        "set_state_4",
        "set_state_5",
        "set_state_6",
        "set_state_7",
        "set_state_8",
        "set_state_9",
    ]

    @admin.action(description="Set selected file status to Unspecified")
    def set_state_0(self, request, queryset):
        queryset.update(state=0)

    @admin.action(description="Set selected file status to Processed")
    def set_state_1(self, request, queryset):
        queryset.update(state=1)

    @admin.action(description="Set selected file status to Active")
    def set_state_2(self, request, queryset):
        queryset.update(state=2)

    @admin.action(description="Set selected file status to Deactivated")
    def set_state_3(self, request, queryset):
        queryset.update(state=3)

    @admin.action(description="Set selected file status to Hidden")
    def set_state_4(self, request, queryset):
        queryset.update(state=4)

    @admin.action(description="Set selected file status to Deprecated")
    def set_state_5(self, request, queryset):
        queryset.update(state=5)

    @admin.action(description="Set selected file status to Archived")
    def set_state_6(self, request, queryset):
        queryset.update(state=6)

    @admin.action(description="Set selected file status to Removed")
    def set_state_7(self, request, queryset):
        queryset.update(state=7)

    @admin.action(description="Set selected file status to Error")
    def set_state_8(self, request, queryset):
        queryset.update(state=8)

    @admin.action(description="Set selected file status to Other")
    def set_state_9(self, request, queryset):
        queryset.update(state=9)


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    """Manage projects"""

    list_display = (
        "id",
        "project_name",
        "cost",
        "max_area",
        "type",
        "state",
        "comment",
        "created_date",
        "updated_date",
        "qgis_project_file",
        "vendor_id",
        "config_pgservice",
        "config_qgis",
        "config_auth",
    )
    list_display_links = ("id", "project_name")
    list_filter = (
        "project_name",
        "cost",
        "max_area",
        "vendor_id",
        "state",
        "created_date",
        "updated_date",
    )
    search_fields = ("project_name", "vendor_id", "cost", "max_area", "comment")
    ordering = ("-created_date",)
    fields = [
        "project_name",
        "vendor_id",
        "cost",
        "max_area",
        "type",
        "buffer_min",
        "buffer_max",
        "buffer_step",
        "buffer_default",
        "icon",
        "preview_image",
        "coverage",
        "state",
        "config_qgis",
        "config_auth",
        "config_pgservice",
        "project_srs",
        "layer_srs",
        "allowed_srs",
        "comment",
        "siblings",
        "tags",
    ]
    actions = [
        "set_state_0",
        "set_state_1",
        "set_state_2",
        "set_state_3",
    ]

    @admin.action(description="Set selected project type to Unspecified")
    def set_state_0(self, request, queryset):
        queryset.update(state=0)

    @admin.action(description="Set selected project type to Other")
    def set_state_1(self, request, queryset):
        queryset.update(state=1)

    @admin.action(description="Set selected project type to QGIS")
    def set_state_2(self, request, queryset):
        queryset.update(state=2)

    @admin.action(description="Set selected project type to PostGIS")
    def set_state_3(self, request, queryset):
        queryset.update(state=3)


@admin.register(models.ProjectCoverageFile)
class ProjectCoverageFileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "file_object",
        "state",
    )
    fields = [
        "file_object",
        "project_id",
        "state",
    ]


@admin.register(models.ProjectDataFile)
class ProjectDataFileAdmin(ResultFileAdmin, admin.ModelAdmin):
    """Manage data files for projects."""

    list_display = (
        "id",
        "file_name",
        "file_object",
        "version",
        "project_id",
        "comment",
        "file_size",
        "file_stored",
        "created_date",
        "updated_date",
    )
    fields = [
        "file_name",
        "file_object",
        "version",
        "comment",
    ]


@admin.register(models.DownloadableDataItem)
class DownloadableDataItemAdmin(ResultFileAdmin, admin.ModelAdmin):
    """Manage data files for download."""

    list_display = (
        "id",
        "vendor_id",
        "file_name",
        "file_object",
        "file_stored",
        "type",
        "state",
        "cost",
        "version",
        "comment",
        "file_size",
        "created_date",
        "updated_date",
    )
    fields = [
        "file_name",
        "file_object",
        "vendor_id",
        "type",
        "state",
        "cost",
        "data_license",
        "data_attribution",
        "data_metadata",
        "abstract",
        "external_link",
        "description",
        "kudos",
        "tags",
        "icon",
        "coverage",
        "preview_image",
        "version",
        "comment",
    ]
