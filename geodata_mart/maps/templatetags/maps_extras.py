from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

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


@register.filter(name="getCsvStringAsList", is_safe=True)
def getCsvStringAsList(csv_string):
    value_list = csv_string.split(",")
    markup = '<ul class="list-group">'
    for i in value_list:
        markup += '<li class="list-group-item">' + i.strip() + "</li>"
    markup += "</ul>"
    return mark_safe(markup)
