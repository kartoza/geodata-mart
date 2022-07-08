from django.core.management.base import BaseCommand
from geodata_mart.users.models import User
from geodata_mart.credits.models import Account
from geodata_mart.maps.models import (
    project_storage,
    StateChoices,
    QgisProjectFile,
    Project,
    Layer,
    ProcessingScriptFile,
)
from django.conf import settings
from geodata_mart.vendors.models import Vendor
from django.core.files import File
import tempfile
from django.conf import settings

from django.core.files.storage import FileSystemStorage


class Command(BaseCommand):
    help = "seed application"

    def transformLabels(self, label):
        mapping = {
            "_exp": "",
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

        self.stdout.write("make credit account for admin...")
        # Assuming that init has run, createsuperuser should make
        # an admin with the id of 1, which needs an account.
        admin = User.objects.get(pk=1)
        # admin = User.objects.get(name="admin")
        admin_accounts = Account.objects.filter(account_owner=admin)
        if not admin_accounts:
            account = Account.objects.create(account_owner=admin, account_balance=100.0)
            del account
        del admin, admin_accounts

        self.stdout.write("make default vendor account")
        kartoza = Vendor.objects.filter(name="Kartoza")
        if not kartoza:
            kartoza = Vendor.objects.create(
                name="Kartoza",
                abstract="Open Source GeoSpatial Solutions",
                description="""Formed by a merger between Linfiniti and AfriSpatial,
            Kartoza is an industry leading Open Source GeoSpatial solutions provider for Africa,
            providing a range of services related to consulting, development, training, and support for customers across the globe.
            """,
            )

        # CREATE THIS FILE MANUALLY BECAUSE THE MANAGEMENT COMMAND RETURNS SuspiciousFileOperation
        # self.stdout.write("create default project file...")
        # project_file = "projects/ngi_sample.qgs"
        # if not project_storage.exists(project_file):
        #     raise Exception(f"{project_storage.path(project_file)} not found")
        # project_file = project_storage.open(project_file, "rb")
        # temp_file = tempfile.NamedTemporaryFile(
        #     dir=settings.STATIC_ROOT
        # )  # try bypass SuspiciousFileOperation
        # # project_file_object = File(project_file)
        # temp_file.write(project_file.read())
        # project_file_object = File(temp_file)
        # ngi_project_file = QgisProjectFile.objects.create(
        #     file_name="NGI Project File",
        #     file_object=project_file_object,
        #     state=StateChoices.OTHER,
        # )
        # project_file.close()
        # project_file_object.close()

        ngi_project_file = QgisProjectFile.objects.filter(
            file_name="NGI Project File"
        ).first()

        self.stdout.write("create default project object...")
        ngi_project = Project.objects.filter(project_name="NGI")
        if not ngi_project:
            ngi_project = Project.objects.create(
                project_name="NGI",
                state=StateChoices.ACTIVE,
                max_area=400,  # 20x20 square kilometers
                project_file=ngi_project_file,
                vendor_id=kartoza,
                comment="The RSA NGI Project with relevant Topo Data",
            )

            self.stdout.write("add project layers...")
            # make sure transformLabels is configured properly
            # layers = {
            #     "cult_barriers_exp": "cult_barriers_exp",
            #     "cult_educational_exp_areal": "cult_educational_exp_areal",
            #     "cult_educational_exp_linear": "cult_educational_exp_linear",
            #     "cult_educational_exp_point": "cult_educational_exp_point",
            #     "cult_industrial_exp_areal": "cult_industrial_exp_areal",
            #     "cult_industrial_exp_linear": "cult_industrial_exp_linear",
            #     "cult_industrial_exp_point": "cult_industrial_exp_point",
            #     "cult_public_exp_areal": "cult_public_exp_areal",
            #     "cult_public_exp_linear": "cult_public_exp_linear",
            #     "cult_public_exp_point": "cult_public_exp_point",
            #     "cult_recreational_exp_areal": "cult_recreational_exp_areal",
            #     "cult_recreational_exp_linear": "cult_recreational_exp_linear",
            #     "cult_recreational_exp_point": "cult_recreational_exp_point",
            #     "cult_utilities_exp_linear": "cult_utilities_exp_linear",
            #     "cult_utilities_exp_point": "cult_utilities_exp_point",
            #     "hydr_areas_exp": "hydr_areas_exp",
            #     "hydr_coastal_areas_exp_areal": "hydr_coastal_areas_exp_areal",
            #     "hydr_coastal_lines_exp": "hydr_coastal_lines_exp",
            #     "hydr_lines_exp": "hydr_lines_exp",
            #     "hydr_points_exp": "hydr_points_exp",
            #     "hyps_elevation_lines_exp": "hyps_elevation_lines_exp",
            #     "hyps_elevation_points_exp": "hyps_elevation_points_exp",
            #     "lclu_landcover_exp": "lclu_landcover_exp",
            #     "lclu_landuse_exp": "lclu_landuse_exp",
            #     "phys_landform_artific_exp_areal": "phys_landform_artific_exp_areal",
            #     "phys_landform_artific_exp_linear": "phys_landform_artific_exp_linear",
            #     "phys_landform_artific_exp_point": "phys_landform_artific_exp_point",
            #     "phys_landform_natural_exp_areal": "phys_landform_natural_exp_areal",
            #     "phys_landform_natural_exp_linear": "phys_landform_natural_exp_linear",
            #     "phys_landform_natural_exp_point": "phys_landform_natural_exp_point",
            #     "tran_crossings_exp_linear": "tran_crossings_exp_linear",
            #     "tran_crossings_exp_point": "tran_crossings_exp_point",
            #     "tran_facilities_exp_areal": "tran_facilities_exp_areal",
            #     "tran_facilities_exp_linear": "tran_facilities_exp_linear",
            #     "tran_facilities_exp_point": "tran_facilities_exp_point",
            #     "tran_line_others_exp": "tran_line_others_exp",
            #     "tran_railway_lines_exp": "tran_railway_lines_exp",
            #     "roads": "roads",
            # }

            layers = {
                "roads": "National Road Network, including National, Provincial, District, and Local roads and paths.",
                "cult_educational_exp_point": "Educational Institutions, including Schools and Universities, from preschool to tertiary institutions.",
                "lclu_landuse_exp": "Land cover and landuse, including residential regions, orchards & vineyards, and other physical landcover.",
            }

            for key, value in layers.items():
                Layer.objects.create(
                    short_name=key,
                    layer_name=self.transformLabels(key),
                    abstract=value,
                    project_id=ngi_project,
                )

        # CREATE THIS FILE MANUALLY BECAUSE THE MANAGEMENT COMMAND RETURNS SuspiciousFileOperation
        # script_file = "processing/scripts/clip_project.py"
        # if not project_storage.exists(script_file):
        #     raise Exception(f"{project_storage.path(script_file)} not found")
        # script_file = project_storage.open(script_file, "rb")
        # script_file_object = File(script_file)
        # ProcessingScriptFile.objects.create(
        #     file_name="Clip QGIS Project",
        #     file_object=script_file_object,
        #     state=StateChoices.OTHER,
        # )
        # script_file_object.close()

        self.stdout.write("time to party...")
