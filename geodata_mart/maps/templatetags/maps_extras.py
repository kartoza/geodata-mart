from django import template
from django.template.defaultfilters import stringfilter

from geodata_mart.maps.models import Job

register = template.Library()


@register.filter(name="subtract")
@stringfilter
def subtract(value, arg):
    return float(value) - float(arg)

@register.filter(name="getJobsFirstTask")
@stringfilter
def getJobsFirstTask(value):
    job_id = value
    job = Job.objects.get(job_id=job_id)
    if not job:
        result = None
    else:
        result = str(job.tasks[0])
    return result
