from django.urls import path
from django.views.generic import TemplateView
from django.conf import settings

from geodata_mart.devapp.views import (
    devapp_map_view,
    nomap
)

app_name = "devapp"
urlpatterns = [
    path(
        "",
        TemplateView.as_view(
            template_name="devapp/links.html", extra_context=dict(debug=settings.DEBUG)
        ),
        name="dev",
    ),
    path(
        "map",
        view=devapp_map_view,
        name="map",
    ),
    path("nomap/<int:project_id>/", nomap, name="nomap"),
]
