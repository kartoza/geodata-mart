from django.http import Http404
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


from geodata_mart.maps.forms import JobForm
from geodata_mart.maps.models import Job


@login_required
def checkout(request, job_id):
    if request.method == "GET":
        job = Job.objects.get(job_id=job_id)
        if not job:
            raise Http404("Job does not exist")
        form = JobForm(instance=job)
        context = {"job": job, "form": form}
        return render(request, "devapp/maps/test_form.html", context)
