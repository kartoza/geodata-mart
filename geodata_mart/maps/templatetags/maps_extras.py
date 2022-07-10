from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter(name="subtract")
@stringfilter
def subtract(value, arg):
    return float(value) - float(arg)
