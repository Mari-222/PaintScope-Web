from django.urls import path

from . import views

app_name = "notificaciones"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("leer-todas/", views.marcar_todas, name="marcar_todas"),
    path("<int:pk>/", views.abrir, name="abrir"),
]
