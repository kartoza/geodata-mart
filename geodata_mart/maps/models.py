from django.db.models.signals import post_delete, pre_save, post_save
from django.dispatch import receiver
from django.db import models
from django.utils.encoding import smart_str
from django.contrib.gis.db import models as gismodels
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import MultiPolygon
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from geodata_mart.vendors.models import Vendor
from geodata_mart.users.models import User
from django.contrib.postgres.fields import ArrayField
from versatileimagefield.fields import VersatileImageField
from PIL import Image
import uuid
import logging

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


class SpatialReferenceSystem(models.Model):
    """AKA Coordinate Reference Systems, SRS, SRSID, CRS, or Map Projections.

    Not directly related to geodjango definitions, but rather for management of
    SRS definitions and requirements in relation to project specs."""

    class SrsTypeChoices(models.IntegerChoices):
        """State choices for processing jobs"""

        UNSPECIFIED = 0, _("Unspecified")
        OTHER = 1, _("Other")
        EPSG = 2, _("EPSG")
        PROJ = 3, _("Proj")
        WKT = 4, _("WKT")
        ESRI = 5, _("ESRI")

    short_name = models.CharField(
        _("SRS Short Name"), max_length=20, blank=True, null=True
    )
    idstring = models.CharField(
        _("SRSID String"), max_length=255, blank=True, null=True
    )
    full_name = models.CharField(
        _("SRS Full Name"), max_length=255, blank=True, null=True
    )
    abstract = models.CharField(_("Abstract"), max_length=255, blank=True, null=True)
    description = models.TextField(verbose_name=_("Description"), blank=True, null=True)
    comment = models.TextField(verbose_name=_("Comments"), blank=True, null=True)
    proj = models.TextField(verbose_name=_("Proj String"), blank=True, null=True)
    wkt = models.TextField(verbose_name=_("WKT Definition"), blank=True, null=True)
    type = models.IntegerField(
        choices=SrsTypeChoices.choices,
        default=SrsTypeChoices.UNSPECIFIED,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = _("SRS")
        verbose_name_plural = _("SRS")

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
        return smart_str(self.name())

    def preview(self):
        return self.description[:100]

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


class PgServiceFile(ManagedFileObject):
    """PostgreSQL Service File Model

    Config files for configuration of the projects QGIS processing environment."""

    def getProjectUploadPath(instance, filename):
        """Get the project media upload path as a callable

        Return the upload path using the current instance detail.

        Returns:
            string: path to output file for image field
        """
        if hasattr(instance, "project_id"):
            if not instance.project_id:
                return f"./configs/pgservice/{filename}"
            else:
                vendor = instance.project_id.vendor_id
                return f"./projects/{vendor.name}/{instance.project_id.project_name}/configs/pgservice/{filename}"
        else:
            return f"./configs/pgservice/{filename}"

    file_object = models.FileField(
        upload_to=getProjectUploadPath,
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

    def getProjectUploadPath(instance, filename):
        """Get the project media upload path as a callable

        Return the upload path using the current instance detail.

        Returns:
            string: path to output file for image field
        """
        if hasattr(instance, "project_id"):
            if not instance.project_id:
                return f"./configs/qgis/{filename}"
            else:
                vendor = instance.project_id.vendor_id
                return f"./projects/{vendor.name}/{instance.project_id.project_name}/configs/qgis/{filename}"
        else:
            return f"./configs/qgis/{filename}"

    file_object = models.FileField(
        upload_to=getProjectUploadPath,
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

    def getProjectUploadPath(instance, filename):
        """Get the project media upload path as a callable

        Return the upload path using the current instance detail.

        Returns:
            string: path to output file for image field
        """
        if hasattr(instance, "project_id"):
            if not instance.project_id:
                return f"./configs/authdb/{filename}"
            else:
                vendor = instance.project_id.vendor_id
                return f"./projects/{vendor.name}/{instance.project_id.project_name}/configs/authdb/{filename}"
        else:
            return f"./configs/authdb/{filename}"

    secret = models.CharField(
        _("Master Key"),
        max_length=255,
        blank=True,
        null=True,
    )
    file_object = models.FileField(
        upload_to=getProjectUploadPath,
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

    def getProjectUploadPath(instance, filename):
        """Get the project media upload path as a callable

        Return the upload path using the current instance detail.

        Returns:
            string: path to output file for image field
        """
        if hasattr(instance, "project_id"):
            if not instance.project_id:
                return f"./projects/{filename}"
            else:
                vendor = instance.project_id.vendor_id
                return f"./projects/{vendor.name}/{instance.project_id.project_name}/{filename}"
        else:
            return f"./projects/{filename}"

    state = models.IntegerField(
        choices=StateChoices.choices, default=StateChoices.UNSPECIFIED
    )
    file_object = models.FileField(
        upload_to=getProjectUploadPath,
        storage=project_storage,
        help_text=_("QGIS project file used for processing sources"),
        verbose_name=_("QGIS project file"),
        blank=False,
        null=False,
    )

    class Meta(ManagedFileObject.Meta):
        verbose_name = _("QGIS Project File")
        verbose_name_plural = _("QGIS Project Files")


class Project(gismodels.Model):
    """GeoData Mart Project Model

    Projects define the collection of layers and processing backend
    used to produce a map interface for regional processing.
    """

    def getImageUploadPath(instance, filename):
        """Get the project media upload path as a callable

        Return the upload path using the current instance detail.

        Returns:
            string: path to output file for image field
        """
        return f"./images/projects/{instance.vendor_id.name}/{instance.project_name}/{filename}"

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
    buffer_min = models.FloatField(
        default=0.0, verbose_name=_("Buffer Min"), blank=False, null=False
    )
    buffer_max = models.FloatField(
        default=10.0, verbose_name=_("Buffer Max"), blank=False, null=False
    )
    buffer_step = models.FloatField(
        default=0.5, verbose_name=_("Buffer Increment"), blank=False, null=False
    )
    buffer_default = models.FloatField(
        default=1, verbose_name=_("Default Buffer (km)"), blank=False, null=False
    )
    max_layers = models.IntegerField(
        default=0, verbose_name=_("Maximum Layers"), blank=True, null=True
    )
    coverage = gismodels.MultiPolygonField(
        default=None,
        verbose_name=_("Project Coverage Region"),
        srid=4326,
        geography=True,
        null=True,
        blank=True,
    )
    icon = VersatileImageField(
        _("Icon"),
        storage=project_storage,
        upload_to=getImageUploadPath,
        blank=True,
        null=True,
    )
    preview_image = VersatileImageField(
        _("Preview"),
        storage=project_storage,
        upload_to=getImageUploadPath,
        blank=True,
        null=True,
    )
    abstract = models.CharField(_("Abstract"), max_length=255, blank=True, null=True)
    external_link = models.CharField(_("Link"), max_length=255, blank=True, null=True)
    description = models.TextField(verbose_name=_("Description"), blank=True, null=True)
    comment = models.TextField(verbose_name=_("Comments"), blank=True, null=True)
    kudos = models.TextField(verbose_name=_("Credits"), blank=True, null=True)
    created_date = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Created Date")
    )
    updated_date = models.DateTimeField(auto_now=True, verbose_name=_("Updated Date"))
    qgis_project_file = models.OneToOneField(
        QgisProjectFile,
        on_delete=models.DO_NOTHING,
        verbose_name=_("QGIS Project File"),
        related_name="project_id",
        null=True,
        blank=True,
    )
    vendor_id = models.ForeignKey(
        Vendor,
        on_delete=models.DO_NOTHING,
        verbose_name=_("Data Vendor"),
        related_name="project_id",
        null=False,
        blank=False,
    )
    config_pgservice = models.OneToOneField(
        PgServiceFile,
        on_delete=models.DO_NOTHING,
        verbose_name=_("PG Service File"),
        related_name="project_id",
        null=True,
        blank=True,
    )
    config_qgis = models.OneToOneField(
        QgisIniFile,
        on_delete=models.DO_NOTHING,
        verbose_name=_("QGIS Configuration File"),
        related_name="project_id",
        null=True,
        blank=True,
    )
    config_auth = models.OneToOneField(
        AuthDbFile,
        on_delete=models.DO_NOTHING,
        verbose_name=_("QGIS Auth DB"),
        related_name="project_id",
        null=True,
        blank=True,
    )
    project_srs = models.ForeignKey(
        SpatialReferenceSystem,
        on_delete=models.DO_NOTHING,
        verbose_name=_("Project SRS"),
        related_name="project_srs",
        null=True,
        blank=True,
    )
    layer_srs = models.ForeignKey(
        SpatialReferenceSystem,
        on_delete=models.DO_NOTHING,
        verbose_name=_("Layer SRS"),
        related_name="layer_srs",
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
        ]

    def __str__(self):
        return self.project_name

    def __unicode__(self):
        return self.project_name

    def preview(self):
        return self.description[:100]

    def gdm_type(self):
        return "project"

    def get_fields(self):
        fields = []
        for field in Job._meta.fields:
            if not field.get_internal_type() == "ArrayField":
                fields.append((field.name, field.value_to_string(self)))
        return fields


class ProjectDataFile(ManagedFileObject):
    """Flat File data for Projects."""

    # TODO management command for bulk management (e.g. autounzip)

    def getProjectUploadPath(instance, filename):
        """Get the project media upload path as a callable

        Return the upload path using the current instance detail.

        Returns:
            string: path to output file for image field
        """
        if hasattr(instance, "project_id"):
            if not instance.project_id:
                return f"./projects/{filename}"
            else:
                vendor = instance.project_id.vendor_id
                return f"./projects/{vendor.name}/{instance.project_id.project_name}/{filename}"
        else:
            return f"./projects/{filename}"

    state = models.IntegerField(
        choices=StateChoices.choices, default=StateChoices.UNSPECIFIED
    )
    file_object = models.FileField(
        upload_to=getProjectUploadPath,
        storage=project_storage,
        help_text=_("Flat file data for use in projects"),
        verbose_name=_("Project data file"),
        blank=False,
        null=False,
    )
    project_id = models.ForeignKey(
        Project,
        on_delete=models.DO_NOTHING,
        verbose_name=_("Project data file"),
        related_name="data_files",
        null=False,
        blank=False,
    )

    class Meta(ManagedFileObject.Meta):
        verbose_name = _("Project data file")
        verbose_name_plural = _("Project data files")


class Layer(models.Model):
    """Project Layers

    This is specific to a specific instance of a project, and does not
    necessarily describe a data source, but rather the QGIS Layer Object.
    """

    def getImageUploadPath(instance, filename):
        """Get the image media upload path as a callable

        Return the upload path using the current instance detail.

        Returns:
            string: path to output file for image field
        """
        if hasattr(instance, "project_id"):
            if not instance.project_id:
                return f"./projects/layers/images/{filename}"
            else:
                vendor = instance.project_id.vendor_id
                return f"./projects/{vendor.name}/{instance.project_id.project_name}/layers/images/{filename}"
        else:
            return f"./projects/layers/images/{filename}"

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
    is_default = models.BooleanField(
        _("Default"),
        help_text=_("Define whether this layer should be checked by default"),
        default=False,
    )
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
    external_link = models.CharField(_("Link"), max_length=255, blank=True, null=True)
    kudos = models.TextField(verbose_name=_("Credits"), blank=True, null=True)
    project_id = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        verbose_name=_("Project"),
        null=False,
        blank=False,
    )
    state = models.IntegerField(
        choices=StateChoices.choices, default=StateChoices.UNSPECIFIED
    )
    lyr_group = models.CharField(_("Layer Group"), max_length=20, blank=True, null=True)
    lyr_class = models.IntegerField(
        choices=LayerClass.choices, default=LayerClass.UNSPECIFIED
    )
    lyr_type = models.IntegerField(
        choices=LayerType.choices, default=LayerType.UNSPECIFIED
    )
    lyr_license = models.TextField(verbose_name=_("License"), blank=True, null=True)
    lyr_attribution = models.TextField(
        verbose_name=_("Attribution"), blank=True, null=True
    )
    lyr_metadata = models.TextField(verbose_name=_("Metadata"), blank=True, null=True)
    kudos = models.TextField(verbose_name=_("Credits"), blank=True, null=True)
    legend_image = VersatileImageField(
        _("Legend"),
        storage=project_storage,
        upload_to=getImageUploadPath,
        blank=True,
        null=True,
    )
    preview_image = VersatileImageField(
        _("Preview"),
        storage=project_storage,
        upload_to=getImageUploadPath,
        blank=True,
        null=True,
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
        return self.description[:100]

    def get_fields(self):
        fields = []
        for field in Job._meta.fields:
            if not field.get_internal_type() == "ArrayField":
                fields.append((field.name, field.value_to_string(self)))
        return fields


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

    def getResultUploadPath(instance, filename):
        """Get the results media upload path as a callable

        Return the upload path using the current instance detail.

        Returns:
            string: path to output file for image field
        """
        return f"./results/{instance.job_id.user_id.id}/{instance.job_id.project_id.project_name}/{filename}"

    file_name = models.CharField(_("File Name"), max_length=255)
    file_object = models.FileField(
        upload_to=getResultUploadPath,
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
        related_name="results",
        null=True,
        blank=True,
    )

    class Meta(ManagedFileObject.Meta):
        verbose_name = _("Result File")
        verbose_name_plural = _("Result Files")


class ProjectCoverageFile(ManagedFileObject):
    """Spatial data file for defining the project coverage

    Must be OGC compliant data source of Type MultiPolygon."""

    def getProjectUploadPath(instance, filename):
        """Get the project media upload path as a callable

        Return the upload path using the current instance detail.

        Returns:
            string: path to output file for image field
        """
        if hasattr(instance, "project_id"):
            if not instance.project_id:
                return f"./projects/coverages/{filename}"
            else:
                vendor = instance.project_id.vendor_id
                return f"./projects/{vendor.name}/{instance.project_id.project_name}/coverages/{filename}"
        else:
            return f"./projects/{filename}"

    class CoverageStateChoices(models.IntegerChoices):
        """State choices for processing jobs"""

        UNSPECIFIED = 0, _("Unspecified")
        LOADED = 1, _("Loaded")
        ERROR = 2, _("Error")

    file_object = models.FileField(
        upload_to=getProjectUploadPath,
        storage=project_storage,
        help_text=_("Spatial data file for definition of project coverage"),
        verbose_name=_("Project Coverage File"),
        blank=True,
        null=True,
    )
    project_id = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        unique=True,
        related_name="coverage_file",
        blank=False,
        null=False,
    )
    state = models.IntegerField(
        choices=CoverageStateChoices.choices,
        default=CoverageStateChoices.UNSPECIFIED,
        blank=True,
        null=True,
    )

    class Meta(ManagedFileObject.Meta):
        verbose_name = _("Project Coverage File")
        verbose_name_plural = _("Project Coverage Files")


class DownloadableDataItem(ManagedFileObject):
    """Flat File objects made available for download."""

    def getDataUploadPath(instance, filename):
        """Get the media upload path as a callable

        Return the upload path using the current instance detail.

        Returns:
            string: path to output file for image field
        """
        return f"./data/{instance.vendor_id.name}/{instance.file_name}/{filename}"

    def getImageUploadPath(instance, filename):
        """Get the image media upload path as a callable

        Return the upload path using the current instance detail.

        Returns:
            string: path to output file for image field
        """
        if hasattr(instance, "project_id"):
            if not instance.project_id:
                return f"./projects/{filename}"
            else:
                vendor = instance.project_id.vendor_id
                return f"./projects/{vendor.name}/{instance.project_id.project_name}/{filename}"
        else:
            return f"./projects/{filename}"

    class DataItemType(models.IntegerChoices):
        """Default state choices for file objects and similar content"""

        UNSPECIFIED = 0, _("Unspecified")
        OTHER = 1, _("Other")
        GPKG = 2, _("GPKG")
        POSTGIS = 3, _("PostGIS")
        RASTER = 4, _("Raster")
        COLLECTION = 5, _("Collection")

    type = models.IntegerField(
        choices=DataItemType.choices, default=DataItemType.UNSPECIFIED
    )
    state = models.IntegerField(
        choices=StateChoices.choices, default=StateChoices.UNSPECIFIED
    )
    file_object = models.FileField(
        upload_to=getDataUploadPath,
        storage=project_storage,
        help_text=_("Downloadable Data Item"),
        verbose_name=_("Data Item"),
        blank=False,
        null=False,
    )
    vendor_id = models.ForeignKey(
        Vendor,
        on_delete=models.DO_NOTHING,
        verbose_name=_("Data Vendor"),
        related_name="data_files",
        null=False,
        blank=False,
    )
    cost = models.FloatField(
        default=0.0, verbose_name=_("Layer Cost"), blank=False, null=False
    )
    icon = VersatileImageField(
        _("Icon"),
        storage=project_storage,
        upload_to=getImageUploadPath,
        blank=True,
        null=True,
    )
    preview_image = VersatileImageField(
        _("Preview"),
        storage=project_storage,
        upload_to=getImageUploadPath,
        blank=True,
        null=True,
    )
    coverage = gismodels.MultiPolygonField(
        default=None,
        verbose_name=_("Data Coverage Region"),
        srid=4326,
        geography=True,
        null=True,
        blank=True,
    )
    data_license = models.TextField(verbose_name=_("License"), blank=True, null=True)
    data_attribution = models.TextField(
        verbose_name=_("Attribution"), blank=True, null=True
    )
    data_metadata = models.TextField(verbose_name=_("Metadata"), blank=True, null=True)
    abstract = models.CharField(_("Abstract"), max_length=255, blank=True, null=True)
    external_link = models.CharField(_("Link"), max_length=255, blank=True, null=True)
    description = models.TextField(verbose_name=_("Description"), blank=True, null=True)
    kudos = models.TextField(verbose_name=_("Credits"), blank=True, null=True)
    tags = models.ManyToManyField(MetaTags, blank=True)

    class Meta(ManagedFileObject.Meta):
        verbose_name = _("Downloadable Data Item")
        verbose_name_plural = _("Downloadable Data Items")

    def gdm_type(self):
        return "download"

    def get_fields(self):
        fields = []
        for field in Job._meta.fields:
            if not field.get_internal_type() == "ArrayField":
                fields.append((field.name, field.value_to_string(self)))
        return fields


@receiver(post_delete, sender=ManagedFileObject)
def delete_files_with_model(sender, instance, **kwargs):
    """Delete file from filesystem when corresponding model with FileField is removed"""
    for field in sender._meta.concrete_fields:
        if isinstance(field, models.FileField):
            file_field = getattr(instance, field.name)
            sender.delete_unused_file(sender, instance, field, file_field)


@receiver(pre_save, sender=ManagedFileObject)
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
                sender.delete_unused_file(sender, instance, field, db_instance_field)


@receiver(post_save, sender=ProjectCoverageFile)
def load_project_coverage_data(sender, instance, **kwargs):
    """Populate coverage field in the related project model

    Use GeoDjango LayerMapping to load OGR data source from
    a file source and load the geometry into the database"""

    try:
        record_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        raise ValueError("Source file record not found")

    ds = DataSource(record_instance.file_object.path)
    layer = ds[0]
    if not layer.geom_type in ["MultiPolygon"]:
        record_instance.state = ProjectCoverageFile.CoverageStateChoices.ERROR
        raise ValueError("The geometry type must be a MultiPolygon")

    try:
        project = Project.objects.get(id=record_instance.project_id.id)
        project.coverage = layer.get_geoms(geos=True)[0]
        project.save()
        record_instance.state = ProjectCoverageFile.CoverageStateChoices.LOADED
    except Exception as e:
        print("Error saving coverage geometry from file")
        print(f"{e}")
        record_instance.state = ProjectCoverageFile.CoverageStateChoices.ERROR


@receiver(post_save, sender=Project)
def resize_icon(sender, instance, **kwargs):
    """Resize the provided image to a maximum size of 600x600"""
    try:
        record_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if not record_instance.icon or not project_storage.exists(
        record_instance.icon.path
    ):
        return

    icon_size = (600, 600)
    icon_image = Image.open(record_instance.icon.path)
    if icon_image.size[0] > icon_size[0] or icon_image.size[1] > icon_size[1]:
        icon_image.thumbnail(icon_size, resample=Image.Resampling.BICUBIC)
        icon_image.save(record_instance.icon.path)


@receiver(post_save, sender=Project)
def resize_preview_image(sender, instance, **kwargs):
    """Resize the provided image to a maximum size of 1200x1200"""
    try:
        record_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if not record_instance.preview_image or not project_storage.exists(
        record_instance.preview_image.path
    ):
        return

    preview_image_size = (1200, 1200)
    preview_image = Image.open(record_instance.preview_image.path)
    if (
        preview_image.size[0] > preview_image_size[0]
        or preview_image.size[1] > preview_image_size[1]
    ):
        preview_image.thumbnail(preview_image_size, resample=Image.Resampling.BICUBIC)
        preview_image.save(record_instance.preview_image.path)


@receiver(post_save, sender=DownloadableDataItem)
def resize_icon(sender, instance, **kwargs):
    """Resize the provided image to a maximum size of 600x600"""
    try:
        record_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if not record_instance.icon or not project_storage.exists(
        record_instance.icon.path
    ):
        return

    icon_size = (600, 600)
    icon_image = Image.open(record_instance.icon.path)
    if icon_image.size[0] > icon_size[0] or icon_image.size[1] > icon_size[1]:
        icon_image.thumbnail(icon_size, resample=Image.Resampling.BICUBIC)
        icon_image.save(record_instance.icon.path)


@receiver(post_save, sender=DownloadableDataItem)
def resize_preview_image(sender, instance, **kwargs):
    """Resize the provided image to a maximum size of 1200x1200"""
    try:
        record_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if not record_instance.preview_image or not project_storage.exists(
        record_instance.preview_image.path
    ):
        return

    preview_image_size = (1200, 1200)
    preview_image = Image.open(record_instance.preview_image.path)
    if (
        preview_image.size[0] > preview_image_size[0]
        or preview_image.size[1] > preview_image_size[1]
    ):
        preview_image.thumbnail(preview_image_size, resample=Image.Resampling.BICUBIC)
        preview_image.save(record_instance.preview_image.path)


@receiver(post_save, sender=Layer)
def resize_legend(sender, instance, **kwargs):
    """Resize the provided image to a maximum size of 600x600"""
    try:
        record_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if not record_instance.legend_image or not project_storage.exists(
        record_instance.legend_image.path
    ):
        return

    legend_size = (600, 600)
    legend_image = Image.open(record_instance.legend_image.path)
    if legend_image.size[0] > legend_size[0] or legend_image.size[1] > legend_size[1]:
        legend_image.thumbnail(legend_size, resample=Image.Resampling.BICUBIC)
        legend_image.save(record_instance.legend_image.path)


@receiver(post_save, sender=Layer)
def resize_preview_image(sender, instance, **kwargs):
    """Resize the provided image to a maximum size of 1200x1200"""
    try:
        record_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if not record_instance.preview_image or not project_storage.exists(
        record_instance.preview_image.path
    ):
        return

    preview_image_size = (1200, 1200)
    preview_image = Image.open(record_instance.preview_image.path)
    if (
        preview_image.size[0] > preview_image_size[0]
        or preview_image.size[1] > preview_image_size[1]
    ):
        preview_image.thumbnail(preview_image_size, resample=Image.Resampling.BICUBIC)
        preview_image.save(record_instance.preview_image.path)
