from django.urls import path

from . import views

app_name = "obras"

urlpatterns = [
    # Artista
    path("portafolio/", views.portafolio, name="portafolio"),
    path("nueva/", views.obra_nueva, name="obra_nueva"),
    path("<int:pk>/editar/", views.obra_editar, name="obra_editar"),
    path("<int:pk>/eliminar/", views.obra_eliminar, name="obra_eliminar"),
    path("<int:pk>/postular/", views.postular, name="postular"),
    path("postulaciones/mias/", views.mis_postulaciones, name="mis_postulaciones"),
    # Curador
    path("postulaciones/", views.postulaciones, name="postulaciones"),
    path("postulaciones/<int:pk>/evaluar/", views.evaluar, name="evaluar"),
    # Eventos temáticos
    path("eventos/", views.eventos, name="eventos"),
    path("eventos/nuevo/", views.evento_nuevo, name="evento_nuevo"),
    path("eventos/<int:pk>/", views.evento_detalle, name="evento_detalle"),
    path("eventos/<int:pk>/editar/", views.evento_editar, name="evento_editar"),
    path("eventos/<int:pk>/publicar/", views.evento_publicar, name="evento_publicar"),
    path("eventos/<int:pk>/incluir/", views.evento_incluir_obra, name="evento_incluir_obra"),
    # Artistas
    path("artistas/", views.artistas, name="artistas"),
    path("artistas/<int:pk>/", views.perfil_artista, name="perfil_artista"),
]
