from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Func, F, Value

from django.core.paginator import (
    Paginator,
    EmptyPage,
    PageNotAnInteger,
)

from geodata_mart.maps.forms import JobForm
from geodata_mart.maps.tasks import process_job_gdmclip
from geodata_mart.maps.models import Project, Layer, Job, ResultFile

import logging

logger = logging.getLogger(__name__)


def gallery(request):
    default_page = 1
    page = request.GET.get("page", default_page)
    projects_list = Project.objects.order_by("id")
    items_per_page = 9
    paginator = Paginator(projects_list, items_per_page)

    try:
        projects_page = paginator.page(page)
    except PageNotAnInteger:
        projects_page = paginator.page(default_page)
    except EmptyPage:
        projects_page = paginator.page(paginator.num_pages)

    context = {"projects": projects_page}
    return render(request, "maps/gallery.html", context)


@login_required
def map(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    project_layers = Layer.objects.filter(project_id=project)
    std_classes = [
        Layer.LayerClass.UNSPECIFIED,
        Layer.LayerClass.STANDARD,
        Layer.LayerClass.OTHER,
    ]
    map_layers = [layer for layer in project_layers if layer.lyr_class in std_classes]
    base_layers = [
        layer for layer in project_layers if layer.lyr_class == Layer.LayerClass.BASE
    ]
    excluded_layers = [
        layer for layer in project_layers if layer.lyr_class == Layer.LayerClass.EXCLUDE
    ]
    coverage = project.coverage.geojson if project.coverage else None
    context = {
        "project": project,
        "coverage": coverage,
        "map_layers": map_layers,
        "base_layers": base_layers,
        "excluded_layers": excluded_layers,
    }
    return render(request, "maps/map.html", context)


@login_required
def cancel_job(request, job_id):
    job = Job.objects.get(job_id=job_id)
    abandoned_state = Job.JobStateChoices.ABANDONED
    if not job:
        raise Http404("Job does not exist")
    if request.method == "POST":
        job.state = abandoned_state
        job.save()
        return HttpResponseRedirect(reverse("maps:results"))
    else:
        return render(request, "maps/cancel.html", {"job": job})


@login_required
def create_job(request):
    if request.method == "GET":
        return HttpResponseRedirect(reverse("maps:results"))
    elif request.method == "POST":
        try:
            # Ensure that a project_id is specified
            get_object_or_404(Project, pk=request.POST.get("project_id"))
            form = JobForm(request.POST)
            if form.errors:
                logger.error(f"{form.errors}")

            if form.is_valid():
                instance = form.save()
                job = Job.objects.get(pk=instance.pk)
                return HttpResponseRedirect(
                    reverse(
                        "maps:checkout",
                        kwargs={"job_id": job.job_id},
                    )
                )
            else:
                messages.add_message(
                    request, messages.ERROR, "The submission was invalid."
                )
                return HttpResponseRedirect(
                    reverse(
                        "maps:map",
                        kwargs={"project_id": form.cleaned_data["project_id"].id},
                    )
                )
        except Project.DoesNotExist:
            raise Http404("Project does not exist")


@login_required
def checkout(request, job_id):
    if request.method == "GET":
        job = Job.objects.get(job_id=job_id)
        if not job:
            raise Http404("Job does not exist")
        form = JobForm(instance=job)
        context = {"job": job, "form": form}
        # return HttpResponseRedirect(reverse("maps:results"))
        # return render(request, "maps/checkout.html", context)
        return render(request, "maps/test_form.html", context)
    elif request.method == "POST":
        job = Job.objects.get(job_id=job_id)
        if not job:
            raise Http404("Job does not exist")
        try:
            # task = process_job_gdmclip.delay(job.job_id)
            task = process_job_gdmclip.apply_async(
                args=[
                    job.job_id,
                ],
                countdown=10,
            )
            messages.add_message(request, messages.INFO, f"Processing {job.job_id}")
        except Exception as e:
            messages.add_message(request, messages.ERROR, f"Error processing task {e}")
        finally:
            # job.tasks.append(task)
            job.tasks = Func(F("tasks"), Value(task.id), function="array_append")
            job.save()
            return HttpResponseRedirect(reverse("maps:results"))


@login_required
def job(request, job_id):
    if request.method == "GET":
        job = Job.objects.get(job_id=job_id)
        if not job:
            raise Http404("Job does not exist")
        context = {"job": job}
        return render(request, "maps/job.html", context)


@login_required
def results(request):
    try:
        jobs = Job.objects.filter(user_id=request.user.id)
    except Job.DoesNotExist:
        raise Http404("There are no jobs for this user")
    ids = [job.id for job in jobs]
    results = ResultFile.objects.filter(job_id__in=ids)
    context = {"jobs": jobs, "results": results}
    return render(request, "maps/results.html", context)
