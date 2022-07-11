from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from geodata_mart.maps.models import Project, Layer


@login_required
def devapp_map_view(request):
    return render(request, "devapp/maps/default.html")


@login_required
def nomap(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    context = {
        "project": project,
        "layers": Layer.objects.filter(project_id=project),
        "excludes_class_list": [Layer.LayerClass.BASE, Layer.LayerClass.EXCLUDE],
    }
    return render(request, "devapp/maps/nomap.html", context)
