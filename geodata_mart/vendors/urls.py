from django.urls import path

from geodata_mart.vendors import views

app_name = "vendors"
urlpatterns = [
    path("messages/", views.msg, name="msg"),
]
