from django.urls import path

from geodata_mart.maps import views

app_name = "maps"
urlpatterns = [
    path("", views.gallery, name="gallery"),
    path("projects/", views.projects, name="projects"),
    path("data/", views.data, name="data"),
    path("maps/<int:project_id>/", views.map, name="map"),
    path("projects/<int:project_id>/", views.detail, name="detail"),
    path("create/", views.create_job, name="create_job"),
    path("job/<job_id>", views.job, name="job"),
    path("checkout/<job_id>", views.checkout, name="checkout"),
    path("cancel/<job_id>", views.cancel_job, name="cancel_job"),
    path("home/", views.results, name="results"),
    path("search/", views.search, name="search"),
]
