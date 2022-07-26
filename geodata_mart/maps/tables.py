import django_tables2 as tables
from geodata_mart.maps.models import Job


class JobTable(tables.Table):
    class Meta:
        model = Job
        template_name = "django_tables2/bootstrap.html"
        fields = (
            "project_id",
            "state",
            "parameters",
            "comment",
        )
