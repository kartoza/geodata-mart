from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.db import models
from django.contrib.gis.db import models as gismodels
from django.contrib.gis.utils import LayerMapping
from django.contrib.gis.gdal import DataSource
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from geodata_mart.vendors.models import Vendor
from geodata_mart.users.models import User
from django.contrib.postgres.fields import ArrayField
import uuid
import logging

# https://stackoverflow.com/questions/1729051/django-upload-to-outside-of-media-root

from django.core.files.storage import FileSystemStorage

project_storage = FileSystemStorage(
    location=settings.QGIS_DATA_ROOT, base_url="/geodata/assets"
)


class StateChoices(models.IntegerChoices):
    """Default state choices for file objects and similar content"""

    UNSPECIFIED = 0, _("Unspecified")
    PROCESSED = 1, _("Processed")
    ACTIVE = 2, _("Active")
    DEACTIVATED = 3, _("Deactivated")
    HIDDEN = 4, _("Hidden")
    DEPRECATED = 5, _("Deprecated")
    ARCHIVED = 6, _("Archived")
    REMOVED = 7, _("Removed")
    ERROR = 8, _("Error")
    OTHER = 9, _("Other")


class MetaTags(models.Model):
    """Metadata tags for search, index, and cataloguing"""

    short_name = models.CharField(_("Tag Short Name"), max_length=20)
    full_name = models.CharField(_("Tag Full Name"), max_length=255)
    abstract = models.CharField(_("Abstract"), max_length=255)
    description = models.TextField(verbose_name=_("Description"), blank=True, null=True)
    comment = models.TextField(verbose_name=_("Comments"), blank=True, null=True)
    related = models.ManyToManyField("self", blank=True)

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")

    def __str__(self):
        return self.short_name

    def __unicode__(self):
        return self.short_name

    def preview(self):
        return self.description[:100]


class ManagedFileObject(models.Model):
    """Parent class for managed files

    Includes methods for managing file field object lifecycle.
    This ensures that files with duplicate names are uniquely identified
    by appending a hash to the file name when a  collision occurs, and
    ensuring that the file object in storage is kept in sync with the
    model state by cascading deletions. Additional methods for introspecting
    file properties, such as a files presence or size on disk, are also included.
    """

    file_name = models.CharField(_("File Name"), max_length=255)
    file_object = models.FileField(
        upload_to="",
        storage=project_storage,
        help_text=_("Managed File Object"),
        verbose_name=_("Managed File Object"),
        blank=True,
        null=True,
    )
    comment = models.TextField(verbose_name=_("Comments"), blank=True, null=True)
    version = models.IntegerField(default=1, blank=False, null=False)
    created_date = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Created Date")
    )
    updated_date = models.DateTimeField(auto_now=True, verbose_name=_("Updated Date"))

    class Meta:
        abstract = True
        verbose_name = _("Managed File Object")
        verbose_name_plural = _("Managed File Objects")
        unique_together = ("file_name", "version")

    def name(self):
        name = str(self.file_name) + " v" + str(self.version)
        return name

    def detail(self):
        detail = str(self.file_name) + " v" + str(self.version)
        return detail

    def __str__(self):
        return self.name()

    def __unicode__(self):
        return self.name()

    def preview(self):
        return self.comment[:100]

    def file_available(self):
        if self.file_object.storage.exists(self.file_object.name):
            return True
        else:
            return False

    def remove_file(self):
        if self.file_available():
            self.file_object.delete(save=False)
            logging.warn(f"File removed: {self.file_object}")
        else:
            raise Exception(f"Cannot remove {self.file_object}: File does not exist")

    def file_size(self):
        if self.file_object.storage.exists(self.file_object.name):
            size_bytes = self.file_object.storage.size(self.file_object.name)
            size_mb = int(size_bytes) / 1024 / 1024
            if size_mb < 1:
                size = round(size_mb, 4)
            else:
                size = round(size_mb, 2)
            return str(size) + " MB"
        else:
            return "0 MB"

    def delete_unused_file(model, instance, field, file_field):
        """Delete the file if not in use by other instances"""
        field_object = {}
        field_object[field.name] = file_field.name
        in_use = model.objects.filter(**field_object).exclude(pk=instance.pk).exists()
        if not in_use:
            file_field.delete(False)

    @receiver(post_delete)
    def delete_files_with_model(sender, instance, **kwargs):
        """Delete file from filesystem when corresponding model with FileField is removed"""
        for field in sender._meta.concrete_fields:
            if isinstance(field, models.FileField):
                file_field = getattr(instance, field.name)
                sender.delete_unused_file(sender, instance, field, file_field)

    @receiver(pre_save)
    def delete_replaced_files(sender, instance, **kwargs):
        """Delete from filesystem when replaced with new file"""
        if not instance.pk:  # exclude initial save
            return
        for field in sender._meta.concrete_fields:
            if isinstance(field, models.FileField):
                try:
                    db_instance = sender.objects.get(pk=instance.pk)
                except sender.DoesNotExist:
                    return
                db_instance_field = getattr(db_instance, field.name)
                file_field = getattr(instance, field.name)
                if db_instance_field.name != file_field.name:
                    sender.delete_unused_file(
                        sender, instance, field, db_instance_field
                    )


class PgServiceFile(ManagedFileObject):
    """PostgreSQL Service File Model

    Config files for configuration of the projects QGIS processing environment."""

    file_object = models.FileField(
        upload_to="./configs/pgservice",
        storage=project_storage,
        help_text=_("PostgreSQL Service File"),
        verbose_name=_("PostgreSQL Service File"),
        blank=False,
        null=False,
    )

    class Meta(ManagedFileObject.Meta):
        verbose_name = _("PostgreSQL Service File")
        verbose_name_plural = _("PostgreSQL Service Files")


class QgisIniFile(ManagedFileObject):
    """QGIS INI Configuration File Model

    Config files for configuration of the projects QGIS processing environment."""

    file_object = models.FileField(
        upload_to="./configs/qgis",
        storage=project_storage,
        help_text=_("QGIS Configuration File"),
        verbose_name=_("QGIS Configuration File"),
        blank=False,
        null=False,
    )

    class Meta(ManagedFileObject.Meta):
        verbose_name = _("QGIS Configuration File")
        verbose_name_plural = _("QGIS Configuration Files")


class AuthDbFile(ManagedFileObject):
    """QGIS Authorization File Model

    Config files for configuration of the projects QGIS processing environment."""

    file_object = models.FileField(
        upload_to="./configs/authdb",
        storage=project_storage,
        help_text=_("QGIS Auth Database"),
        verbose_name=_("QGIS Auth Database"),
        blank=False,
        null=False,
    )

    class Meta(ManagedFileObject.Meta):
        verbose_name = _("QGIS Auth Database")
        verbose_name_plural = _("QGIS Auth Databases")


class ProcessingScriptFile(ManagedFileObject):
    """QGIS Processing Script File

    Config files for configuration of the projects QGIS processing environment."""

    file_object = models.FileField(
        upload_to="./processing/scripts",
        storage=project_storage,
        help_text=_("QGIS Processing Script"),
        verbose_name=_("QGIS Processing Script"),
        blank=False,
        null=False,
    )

    class Meta(ManagedFileObject.Meta):
        verbose_name = _("QGIS Processing Script")
        verbose_name_plural = _("QGIS Processing Scripts")


class ProcessingModelFile(ManagedFileObject):
    """QGIS Processing Model File

    Config files for configuration of the projects QGIS processing environment."""

    file_object = models.FileField(
        upload_to="./processing/models",
        storage=project_storage,
        help_text=_("QGIS Processing Model"),
        verbose_name=_("QGIS Processing Model"),
        blank=False,
        null=False,
    )

    class Meta(ManagedFileObject.Meta):
        verbose_name = _("QGIS Processing Model")
        verbose_name_plural = _("QGIS Processing Models")


class QgisProjectFile(ManagedFileObject):
    """QGIS Project File Model

    QGIS Projects are used as the authoritative source of truth for
    defining collections of layers in a format that can be processed
    using the clip and ship algorithm when using the QGIS project type."""

    state = models.IntegerField(
        choices=StateChoices.choices, default=StateChoices.UNSPECIFIED
    )
    file_object = models.FileField(
        upload_to="./projects",
        storage=project_storage,
        help_text=_("QGIS project file used for processing sources"),
        verbose_name=_("QGIS project file"),
        blank=True,
        null=True,
    )

    class Meta(ManagedFileObject.Meta):
        verbose_name = _("QGIS Project File")
        verbose_name_plural = _("QGIS Project Files")


class Project(gismodels.Model):
    """GeoData Mart Project Model

    Projects define the collection of layers and processing backend
    used to produce a map interface for regional processing.
    """

    class ProjectType(models.IntegerChoices):
        """Default state choices for file objects and similar content"""

        UNSPECIFIED = 0, _("Unspecified")
        OTHER = 1, _("Other")
        QGIS = 2, _("QGIS")
        POSTGIS = 3, _("PostGIS")

    project_name = models.CharField(_("Project Name"), max_length=255)
    type = models.IntegerField(choices=ProjectType.choices, default=ProjectType.QGIS)
    state = models.IntegerField(
        choices=StateChoices.choices, default=StateChoices.UNSPECIFIED
    )
    cost = models.FloatField(
        default=0.0, verbose_name=_("Unit Cost"), blank=False, null=False
    )
    max_area = models.FloatField(
        default=None,
        verbose_name=_("Maximum Processing Area"),
        null=True,
        blank=True,
    )
    coverage = gismodels.MultiPolygonField(
        default=None,
        verbose_name=_("Project Coverage Region"),
        null=True,
        blank=True,
    )
    image = models.ImageField(upload_to="images/projects")
    comment = models.TextField(verbose_name=_("Comments"), blank=True, null=True)
    created_date = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Created Date")
    )
    updated_date = models.DateTimeField(auto_now=True, verbose_name=_("Updated Date"))
    project_file = models.ForeignKey(
        QgisProjectFile,
        on_delete=models.CASCADE,
        verbose_name=_("Project File"),
        null=False,
        blank=False,
    )
    vendor_id = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        verbose_name=_("Data Vendor"),
        null=False,
        blank=False,
    )
    config_pgservice = models.ForeignKey(
        PgServiceFile,
        on_delete=models.CASCADE,
        verbose_name=_("PG Service File"),
        null=True,
        blank=True,
    )
    config_qgis = models.ForeignKey(
        QgisIniFile,
        on_delete=models.CASCADE,
        verbose_name=_("QGIS Configuration File"),
        null=True,
        blank=True,
    )
    config_auth = models.ForeignKey(
        AuthDbFile,
        on_delete=models.CASCADE,
        verbose_name=_("QGIS Auth DB"),
        null=True,
        blank=True,
    )
    siblings = models.ManyToManyField("self", blank=True)
    tags = models.ManyToManyField(MetaTags, blank=True)

    class Meta:
        ordering = [
            "vendor_id",
            "updated_date",
            "created_date",
            "project_name",
            "project_file",
        ]

    def __str__(self):
        return self.project_name

    def __unicode__(self):
        return self.project_name

    def preview(self):
        return self.comment[:100]


class Layer(models.Model):
    """Project Layers

    This is specific to a specific instance of a project, and does not
    necessarily describe a data source, but rather the QGIS Layer Object.
    """

    class LayerClass(models.IntegerChoices):
        """Default state choices for file objects and similar content"""

        UNSPECIFIED = 0, _("Unspecified")
        STANDARD = 1, _("Standard")
        BASE = 2, _("Base")
        EXCLUDE = 3, _("Exclude")
        OTHER = 4, _("Other")

    class LayerType(models.IntegerChoices):
        """Default state choices for file objects and similar content"""

        UNSPECIFIED = 0, _("Unspecified")
        VECTOR = 1, _("Vector")
        RASTER = 2, _("Raster")
        MESH = 3, _("Mesh")
        WMS = 4, _("WMS")
        XYZ = 5, _("XYZ")
        WFS = 6, _("WFS")  # WFS/ OGC API Features
        VECTORTILE = 7, _("Vector Tile")
        TABLE = 8, _("Table")
        OTHER = 9, _("Other")

    short_name = models.CharField(_("Layer Short Name"), max_length=80)
    layer_name = models.CharField(_("Layer Name"), max_length=255)
    abstract = models.CharField(_("Layer Abstract"), max_length=255)
    created_date = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Created Date")
    )
    updated_date = models.DateTimeField(auto_now=True, verbose_name=_("Updated Date"))
    cost = models.FloatField(
        default=0.0, verbose_name=_("Layer Cost"), blank=False, null=False
    )
    cost_modifier = models.FloatField(
        default=1.0, verbose_name=_("Layer Cost Modifier"), blank=False, null=False
    )
    description = models.TextField(
        verbose_name=_("Layer Description"), blank=True, null=True
    )
    comment = models.TextField(verbose_name=_("Comments"), blank=True, null=True)
    project_id = models.ForeignKey(
        Project,
        on_delete=models.DO_NOTHING,
        verbose_name=_("Project"),
        null=False,
        blank=False,
    )
    state = models.IntegerField(
        choices=StateChoices.choices, default=StateChoices.UNSPECIFIED
    )
    lyr_group = models.CharField(_("Layer Group"), max_length=20)
    lyr_class = models.IntegerField(
        choices=LayerClass.choices, default=LayerClass.UNSPECIFIED
    )
    lyr_type = models.IntegerField(
        choices=LayerType.choices, default=LayerType.UNSPECIFIED
    )
    siblings = models.ManyToManyField("self", blank=True)
    tags = models.ManyToManyField(MetaTags, blank=True)

    class Meta:
        verbose_name = _("Project Layer")
        verbose_name_plural = _("Project Layers")
        unique_together = ("short_name", "project_id")

    def __str__(self):
        return self.short_name

    def __unicode__(self):
        return self.short_name

    def preview(self):
        return self.comment[:100]


class Job(models.Model):
    """Processing Jobs

    Each processing request and its execution lifecycle should be monitored
    and assigned to a distinct instance of this model which is logged for the
    purpose of status checks, retrieval of results, and auditing.
    """

    class JobStateChoices(models.IntegerChoices):
        """State choices for processing jobs"""

        UNSPECIFIED = 0, _("Unspecified")
        ABANDONED = 1, _("Abandoned")
        UNFULFILLED = 2, _("Unfulfilled")
        PROCESSED = 3, _("Processed")
        COMPLETED = 4, _("Completed")
        FAILED = 5, _("Failed")
        PROCESSING = 6, _("Processing")
        UNKNOWN = 7, _("Unknown")
        STALE = 8, _("Stale")
        OTHER = 9, _("Other")

    job_id = models.UUIDField(
        _("Job ID"),
        primary_key=False,
        default=uuid.uuid4,
        editable=True,
        blank=True,
        null=True,
    )
    created_date = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Created Date")
    )
    updated_date = models.DateTimeField(auto_now=True, verbose_name=_("Updated Date"))
    user_id = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        verbose_name=_("User"),
        null=False,
        blank=False,
    )
    project_id = models.ForeignKey(
        Project,
        on_delete=models.DO_NOTHING,
        verbose_name=_("Project"),
        null=False,
        blank=False,
    )
    layers = models.ManyToManyField(Layer, verbose_name=_("Map Layers"), blank=True)
    state = models.IntegerField(
        choices=JobStateChoices.choices,
        default=JobStateChoices.UNSPECIFIED,
        blank=True,
        null=True,
    )
    parameters = models.JSONField(_("Request Parameters"), blank=True, null=True)
    tasks = ArrayField(models.CharField(max_length=36), blank=True, null=True)
    comment = models.TextField(verbose_name=_("Comments"), blank=True, null=True)

    class Meta:
        verbose_name = _("Geodata Mart Processing Job")
        verbose_name_plural = _("Geodata Mart Processing Jobs")

    def __str__(self):
        return str(self.job_id)

    def __unicode__(self):
        return str(self.job_id)

    def preview(self):
        return self.comment[:100]

    def get_fields(self):
        # return [(field.name, field.value_to_string(self)) for field in Job._meta.fields]
        fields = []
        for field in Job._meta.fields:
            if not field.get_internal_type() == "ArrayField":
                # if not field.name == "tasks":
                fields.append((field.name, field.value_to_string(self)))
            # elif field.name == "tasks" and field:
            #     tasks = []
            #     for el in field.items():  # how to iterate?
            #         tasks.append((el.name, el.value_to_string(self)))
            #     fields.append(("tasks", tasks))
        return fields


class ResultFile(ManagedFileObject):
    """Processing Job Result File Model

    Model for the resulting file objects produced by processing jobs."""

    file_name = models.CharField(_("File Name"), max_length=255)
    file_object = models.FileField(
        upload_to="./output",
        storage=project_storage,
        help_text=_("Resulting output file from processing jobs"),
        verbose_name=_("Results File"),
        blank=True,
        null=True,
    )
    job_id = models.ForeignKey(
        Job,
        on_delete=models.DO_NOTHING,
        verbose_name=_("Job"),
        null=True,
        blank=True,
    )

    class Meta(ManagedFileObject.Meta):
        verbose_name = _("Result File")
        verbose_name_plural = _("Result Files")
