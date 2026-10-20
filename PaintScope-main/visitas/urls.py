from django.urls import path

from . import views

app_name = "visitas"

urlpatterns = [
    path("mis-visitas/", views.mis_visitas, name="mis_visitas"),
    path("obra/<int:obra_id>/agendar/", views.agendar, name="agendar"),
    path("<int:pk>/cancelar/", views.cancelar, name="cancelar"),
]
