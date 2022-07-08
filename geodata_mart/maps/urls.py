from django.urls import path, re_path

from geodata_mart.maps import views

app_name = "maps"
urlpatterns = [
    path("", views.gallery, name="gallery"),
    path("<int:project_id>/", views.map, name="map"),
    path("nomap/<int:project_id>/", views.nomap, name="nomap"),
    path("create/", views.create_job, name="create_job"),
    path("checkout/<job_id>", views.checkout, name="checkout"),
    path("cancel/<job_id>", views.cancel_job, name="cancel_job"),
    path("data/", views.results, name="results"),
]
