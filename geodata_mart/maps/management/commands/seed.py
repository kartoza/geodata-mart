import os
from asyncore import file_dispatcher
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
    ProjectCoverageFile,
    ProjectDataFile,
    SpatialReferenceSystem,
)
from django.conf import settings
from geodata_mart.vendors.models import Vendor
from django.conf import settings
from os.path import basename
from qgis.core import *

QgsApplication.setPrefixPath("/usr/bin/qgis", True)
qgs = QgsApplication([], False)
qgs.initQgis()
project = QgsProject.instance()


class Command(BaseCommand):
    help = "seed application"

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


        crs_list = ["4326", "3587", "9221"]
        for crs in crs_list:
            srs = SpatialReferenceSystem.objects.create(
                short_name=crs,
                idstring="EPSG:" + crs,
            )
            srs.save()

        crs4326 = SpatialReferenceSystem.objects.get(short_name="4326")
        crs3587 = SpatialReferenceSystem.objects.get(short_name="3587")
        crs9221 = SpatialReferenceSystem.objects.get(short_name="9221")

        self.stdout.write("get default project object...")
        qgis_projects_path = '/app/geodata/projects/Kartoza'
        for root, dir_names, file_name_base in os.walk(qgis_projects_path):
            for filename in file_name_base:
                ext = os.path.splitext(filename)[1].lower()
                if ext in '.qgz, .qgs':
                    file_base = os.path.splitext(filename)[0]
                    full_path = os.path.join(root, file_base) + ext

        ngi_project = Project.objects.filter(project_name="NGI").first()
        # auth_db = AuthDbFile.objects.filter(file_name="kartozagis_qgis").first()
        if not ngi_project:
            self.stdout.write("create default project object...")
            ngi_project = Project.objects.create(
                project_name="NGI",
                state=StateChoices.ACTIVE,
                max_area=400,  # 20x20 square kilometers
                # config_auth=auth_db,
                vendor_id=kartoza,
                project_srs=crs9221,
                layer_srs=crs9221,
                description="Topographic data from the National Geospatial Information Catalog for the Republic of South Africa",
            )

            self.stdout.write("add project layers...")
            project.read('/app/geodata/projects/Kartoza/NGI/ngi.qgs')
            layers_info = [
                (layer.name(), layer.abstract() if layer.abstract() and layer.abstract().strip() else layer.name()) for
                layer in QgsProject.instance().mapLayers().values() if layer.type() == QgsMapLayerType.VectorLayer]
            layers = {name: name for name, _ in layers_info}
            # make sure transformLabels is configured properly
            for key, value in layers.items():
                Layer.objects.create(
                    short_name=key,
                    layer_name=key,
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

            self.stdout.write("add project preview...")
            preview_image = "seed/ngi_preview.png"
            if not project_storage.exists(preview_image):
                raise Exception(f"{project_storage.path(preview_image)} not found")

            with project_storage.open(preview_image) as f:
                ngi_project.preview_image.save(basename(preview_image), f, save=True)

        self.stdout.write("create default project file...")
        project_file = "seed/ngi.qgs"
        if not project_storage.exists(project_file):
            raise Exception(f"{project_storage.path(project_file)} not found")
        ngi_project_file = QgisProjectFile.objects.create(
            file_name="NGI Project File",
            state=StateChoices.OTHER,
            project_id=ngi_project,
        )

        with project_storage.open(project_file) as f:
            ngi_project_file.file_object.save(basename(project_file), f, save=True)

        ngi_project.qgis_project_file = ngi_project_file
        ngi_project.save()

        # self.stdout.write("add default project coverage...")
        # if not ngi_project.coverage:

        #     coverage_file = "seed/rsa_aoi_4326.geojson"
        #     if not project_storage.exists(coverage_file):
        #         raise Exception(f"{project_storage.path(coverage_file)} not found")

        #     coverage = ProjectCoverageFile.objects.create(
        #         file_name="rsa_aoi_4326",
        #         project_id=ngi_project,
        #     )

        #     with project_storage.open(coverage_file) as f:
        #         coverage.file_object.save(basename(coverage_file), f, save=True)

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
            vendor_id=kartoza,
            kudos="Charlie, Natural Earth Data",
            description=("Simple global base map made from high level data ")
                        + ("from the Natural Earth data collection. Includes a QGIS project ")
                        + (
                            "and source data in Geopackage Format and includes dark and light themes."
                        ),
        )

        with project_storage.open(data_file) as f:
            data_record.file_object.save(basename(data_file), f, save=True)

        preview_image = "seed/natural_earth.png"
        if not project_storage.exists(preview_image):
            raise Exception(f"{project_storage.path(preview_image)} not found")

        with project_storage.open(preview_image) as f:
            data_record.preview_image.save(basename(preview_image), f, save=True)

        self.stdout.write("get osm project object...")
        osm_project = Project.objects.filter(project_name="RSA OSM").first()
        # auth_db = AuthDbFile.objects.filter(file_name="kartozagis_qgis").first()
        if not osm_project:
            self.stdout.write("create osm project object...")
            osm_project = Project.objects.create(
                project_name="RSA OSM",
                state=StateChoices.ACTIVE,
                max_area=400,  # 20x20 square kilometers
                # config_auth=auth_db,
                vendor_id=kartoza,
                project_srs=crs9221,
                layer_srs=crs9221,
                description="OpenStreetMap data project produced from GeoFabrik regional downloads for South Africa.",
            )

            self.stdout.write("add project layers...")
            # make sure transformLabels is configured properly
            layers = {
                "gis_osm_buildings_a_free_1": "gis_osm_buildings_a_free_1",
                "gis_osm_landuse_a_free_1": "gis_osm_landuse_a_free_1",
                "gis_osm_natural_a_free_1": "gis_osm_natural_a_free_1",
                "gis_osm_natural_free_1": "gis_osm_natural_free_1",
                "gis_osm_places_a_free_1": "gis_osm_places_a_free_1",
                "gis_osm_places_free_1": "gis_osm_places_free_1",
                "gis_osm_pofw_a_free_1": "gis_osm_pofw_a_free_1",
                "gis_osm_pofw_free_1": "gis_osm_pofw_free_1",
                "gis_osm_pois_a_free_1": "gis_osm_pois_a_free_1",
                "gis_osm_pois_free_1": "gis_osm_pois_free_1",
                "gis_osm_railways_free_1": "gis_osm_railways_free_1",
                "gis_osm_roads_free_1": "gis_osm_roads_free_1",
                "gis_osm_traffic_a_free_1": "gis_osm_traffic_a_free_1",
                "gis_osm_traffic_free_1": "gis_osm_traffic_free_1",
                "gis_osm_transport_a_free_1": "gis_osm_transport_a_free_1",
                "gis_osm_transport_free_1": "gis_osm_transport_free_1",
                "gis_osm_water_a_free_1": "gis_osm_water_a_free_1",
                "gis_osm_waterways_free_1": "gis_osm_waterways_free_1",
                "land_polygons": "land_polygons",
                "water_polygons": "water_polygons",
            }

            for key, value in layers.items():
                Layer.objects.create(
                    short_name=key,
                    layer_name=self.transformLabels(key),
                    abstract=value,
                    project_id=osm_project,
                    lyr_class=Layer.LayerClass.STANDARD,
                )

            self.stdout.write("add osm project preview...")
            preview_image = "seed/rsa_osm_preview.png"
            if not project_storage.exists(preview_image):
                raise Exception(f"{project_storage.path(preview_image)} not found")

            with project_storage.open(preview_image) as f:
                osm_project.preview_image.save(basename(preview_image), f, save=True)

            self.stdout.write("add osm source geopackage...")
            gpkg_file = "seed/rsa_osm.gpkg"
            if not project_storage.exists(gpkg_file):
                raise Exception(f"{project_storage.path(gpkg_file)} not found")
            gpkg_record = ProjectDataFile.objects.create(
                file_name="rsa_osm.gpkg",
                project_id=osm_project,
            )

            with project_storage.open(gpkg_file) as f:
                gpkg_record.file_object.save(basename(gpkg_file), f, save=True)

        self.stdout.write("create osm project file...")
        project_file = "seed/rsa_osm.qgs"
        if not project_storage.exists(project_file):
            raise Exception(f"{project_storage.path(project_file)} not found")
        osm_project_file = QgisProjectFile.objects.create(
            file_name="RSA OSM Project File",
            state=StateChoices.OTHER,
            project_id=osm_project,
        )
        osm_project.qgis_project_file = osm_project_file
        osm_project.save()

        with project_storage.open(project_file) as f:
            osm_project_file.file_object.save(basename(project_file), f, save=True)

        self.stdout.write("time to party...")
