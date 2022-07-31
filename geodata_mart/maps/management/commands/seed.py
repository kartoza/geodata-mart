from django.core.management.base import BaseCommand
from geodata_mart.users.models import User
from geodata_mart.credits.models import Account
from geodata_mart.maps.models import (
    project_storage,
    StateChoices,
    QgisProjectFile,
    Project,
    Layer,
    AuthDbFile,
    ProcessingScriptFile,
    DownloadableDataItem,
    ProjectDataFile,
)
from django.conf import settings
from geodata_mart.vendors.models import Vendor
from django.conf import settings
from os.path import basename


class Command(BaseCommand):
    help = "seed application"

    def transformLabels(self, label):
        mapping = {
            "_exp": "",
            "exp_": "",
            "_exp_": "_",
            "lclu_": "",
            "landform_artific": "Artificial Landform",
            "landform_natural": "Natural Landform",
            "tran_": "Transport ",
            "hydr_": "Hydrographic ",
            "hyps_": "Hypsographic ",
            "cult_": "Cultural ",
            "linear": "Lines",
            "point": "Points",
            "areal": "Areas",
            "educational": "Education",
            "_": " ",
            "-": " ",
            "  ": " ",  # replace any double spaces
            "  ": " ",
            "  ": " ",
            "  ": " ",
            "  ": " ",
        }

        for key, value in mapping.items():
            label = label.replace(key, value)

        label = label.title()
        label = label.strip()

        return label

    def handle(self, *args, **options):
        self.stdout.write("starting seed...")

        self.stdout.write("make default vendor account")
        kartoza = Vendor.objects.filter(name="Kartoza")
        if not kartoza:
            kartoza = Vendor.objects.create(
                name="Kartoza",
                abstract="Open Source GeoSpatial Solutions",
                description=(
                    "Formed by a merger between Linfiniti and AfriSpatial,"
                    + " Kartoza is an industry leading Open Source GeoSpatial solutions"
                    + " provider for Africa, providing a range of services related to"
                    + " consulting, development, training, and support for customers across the globe."
                ),
            )
        else:
            kartoza = kartoza.first()

        # cleanup
        # Project.objects.all().delete()
        # QgisProjectFile.objects.all().delete()
        # Layer.objects.all().delete()

        self.stdout.write("create default project file...")
        project_file = "seed/ngi.qgs"
        if not project_storage.exists(project_file):
            raise Exception(f"{project_storage.path(project_file)} not found")
        ngi_project_file = QgisProjectFile.objects.create(
            file_name="NGI Project File",
            state=StateChoices.OTHER,
        )

        with project_storage.open(project_file) as f:
            ngi_project_file.file_object.save(basename(project_file), f, save=True)

        self.stdout.write("load auth database...")
        db_file = "seed/kartozagis_qgis.db"
        if not project_storage.exists(db_file):
            raise Exception(f"{project_storage.path(db_file)} not found")
        db_record = AuthDbFile.objects.create(
            file_name="kartozagis_qgis",
            secret=settings.QGISAUTHDBSEEDPW,
        )

        with project_storage.open(db_file) as f:
            db_record.file_object.save(basename(db_file), f, save=True)

        self.stdout.write("create default project object...")
        ngi_project = Project.objects.filter(project_name="NGI").first()
        auth_db = AuthDbFile.objects.filter(file_name="kartozagis_qgis").first()
        if not ngi_project:
            ngi_project = Project.objects.create(
                project_name="NGI",
                state=StateChoices.ACTIVE,
                max_area=400,  # 20x20 square kilometers
                qgis_project_file=ngi_project_file,
                config_auth=auth_db,
                vendor_id=kartoza,
                comment="Topographic data from the National Geospatial Information Catalog for the Republic of South Africa",
            )

            self.stdout.write("add project layers...")
            # make sure transformLabels is configured properly
            layers = {
                "cult_barriers_exp": "cult_barriers_exp",
                "cult_educational_exp_areal": "cult_educational_exp_areal",
                "cult_educational_exp_linear": "cult_educational_exp_linear",
                "cult_educational_exp_point": "Educational Institutions, including Schools and Universities, from preschool to tertiary institutions.",
                "cult_industrial_exp_areal": "cult_industrial_exp_areal",
                "cult_industrial_exp_linear": "cult_industrial_exp_linear",
                "cult_industrial_exp_point": "cult_industrial_exp_point",
                "cult_public_exp_areal": "cult_public_exp_areal",
                "cult_public_exp_linear": "cult_public_exp_linear",
                "cult_public_exp_point": "cult_public_exp_point",
                "cult_recreational_exp_areal": "cult_recreational_exp_areal",
                "cult_recreational_exp_linear": "cult_recreational_exp_linear",
                "cult_recreational_exp_point": "cult_recreational_exp_point",
                "cult_utilities_exp_linear": "cult_utilities_exp_linear",
                "cult_utilities_exp_point": "cult_utilities_exp_point",
                "hydr_areas_exp": "hydr_areas_exp",
                "hydr_coastal_areas_exp_areal": "hydr_coastal_areas_exp_areal",
                "hydr_coastal_lines_exp": "hydr_coastal_lines_exp",
                "hydr_lines_exp": "hydr_lines_exp",
                "hydr_points_exp": "hydr_points_exp",
                "hyps_elevation_lines_exp": "hyps_elevation_lines_exp",
                "hyps_elevation_points_exp": "hyps_elevation_points_exp",
                "lclu_landcover_exp": "Land Cover, including barren land, cultivated land, and other landcover types.",
                "lclu_landuse_exp": "Land Use, including residential regions, orchards & vineyards, and other physical land use types.",
                "phys_landform_artific_exp_areal": "phys_landform_artific_exp_areal",
                "phys_landform_artific_exp_linear": "phys_landform_artific_exp_linear",
                "phys_landform_artific_exp_point": "phys_landform_artific_exp_point",
                "phys_landform_natural_exp_areal": "phys_landform_natural_exp_areal",
                "phys_landform_natural_exp_linear": "phys_landform_natural_exp_linear",
                "phys_landform_natural_exp_point": "phys_landform_natural_exp_point",
                "tran_crossings_exp_linear": "tran_crossings_exp_linear",
                "tran_crossings_exp_point": "tran_crossings_exp_point",
                "tran_facilities_exp_areal": "tran_facilities_exp_areal",
                "tran_facilities_exp_linear": "tran_facilities_exp_linear",
                "tran_facilities_exp_point": "tran_facilities_exp_point",
                "tran_line_others_exp": "tran_line_others_exp",
                "tran_railway_lines_exp": "tran_railway_lines_exp",
                "roads": "National Road Network, including National, Provincial, District, and Local roads and paths.",
            }

            for key, value in layers.items():
                Layer.objects.create(
                    short_name=key,
                    layer_name=self.transformLabels(key),
                    abstract=value,
                    project_id=ngi_project,
                    lyr_class=Layer.LayerClass.STANDARD,
                )

            # add ngi project base layers
            Layer.objects.create(
                short_name="rsaortho",
                layer_name="OSM-NGI-Ortho",
                is_default=True,
                abstract="NGI Imagery Mosaic generated and hosted as a WMS by the OpenStreetMap Team",
                project_id=ngi_project,
                lyr_class=Layer.LayerClass.BASE,
                lyr_type=Layer.LayerType.WMS,
            )
            Layer.objects.create(
                short_name="osm",
                layer_name="OpenStreetMap",
                is_default=True,
                abstract="OpenStreetMap Basic Global XYZ Tile Layer",
                project_id=ngi_project,
                lyr_class=Layer.LayerClass.BASE,
                lyr_type=Layer.LayerType.XYZ,
            )
            Layer.objects.create(
                short_name="worlddem",
                layer_name="Mapzen Global Terrain",
                is_default=False,
                abstract="Mapzen Global Terrain, hosted by Amazon Web Services. Note that this layer only renders properly on QGIS version 3.26 and higher.",
                project_id=ngi_project,
                lyr_class=Layer.LayerClass.EXCLUDE,
                lyr_type=Layer.LayerType.XYZ,
            )

        self.stdout.write("load processing script...")
        script_file = "seed/clip_project.py"
        if not project_storage.exists(script_file):
            raise Exception(f"{project_storage.path(script_file)} not found")
        script_record = ProcessingScriptFile.objects.create(
            file_name="script:gdmclip",
        )

        with project_storage.open(script_file) as f:
            script_record.file_object.save(basename(script_file), f, save=True)

        self.stdout.write("load natural earth data item...")
        data_file = "seed/natural_earth.gpkg"
        if not project_storage.exists(data_file):
            raise Exception(f"{project_storage.path(data_file)} not found")
        data_record = DownloadableDataItem.objects.create(
            file_name="Natural Earth",
            vendor_id = kartoza,
            kudos="Charlie, Natural Earth Data",
            description=("Simple global base map made from high level data ")
            + ("from the Natural Earth data collection. Includes a QGIS project ")
            + ("and source data in Geopackage Format and includes dark and light themes.")
        )

        with project_storage.open(data_file) as f:
            data_record.file_object.save(basename(data_file), f, save=True)

        preview_image = "seed/natural_earth.png"
        if not project_storage.exists(preview_image):
            raise Exception(f"{project_storage.path(preview_image)} not found")

        with project_storage.open(preview_image) as f:
            data_record.preview_image.save(basename(preview_image), f, save=True)

        self.stdout.write("create placeholder projects...")

        for i in range(25):
            Project.objects.create(
                project_name="Blank " + str(i + 2),
                state=StateChoices.ACTIVE,
                vendor_id=kartoza,
                comment="Blank project spec for testing gallery view, number: "
                + str(i + 2),
            )

        self.stdout.write("time to party...")
