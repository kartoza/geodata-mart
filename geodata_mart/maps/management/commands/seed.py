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
        project_file = "seed/ngi_sample.qgs"
        if not project_storage.exists(project_file):
            raise Exception(f"{project_storage.path(project_file)} not found")
        ngi_project_file = QgisProjectFile.objects.create(
            file_name="NGI Project File",
            state=StateChoices.OTHER,
        )

        ngi_project_file.file_object.save(
            basename(project_file), project_storage.open(project_file), save=True
        )

        self.stdout.write("create default project object...")
        ngi_project = Project.objects.filter(project_name="NGI").first()
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

        self.stdout.write("load processing script...")
        script_file = "seed/clip_project.py"
        if not project_storage.exists(script_file):
            raise Exception(f"{project_storage.path(script_file)} not found")
        script_record = ProcessingScriptFile.objects.create(
            file_name="script:gdmclip",
        )

        script_record.file_object.save(
            basename(script_file), project_storage.open(script_file), save=True
        )

        self.stdout.write("create placeholder projects...")

        for i in range(26):
            Project.objects.create(
                project_name="Blank" + str(i + 2),
                state=StateChoices.ACTIVE,
                vendor_id=kartoza,
                comment="Blank project spec for testing gallery view, number: "
                + str(i+2),
            )

        self.stdout.write("time to party...")
