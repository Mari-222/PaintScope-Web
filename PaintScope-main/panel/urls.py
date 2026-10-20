from django.urls import path

from . import views

app_name = "panel"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("usuarios/", views.usuarios, name="usuarios"),
    path("usuarios/nuevo/", views.usuario_nuevo, name="usuario_nuevo"),
    path("usuarios/<int:pk>/editar/", views.usuario_editar, name="usuario_editar"),
    path("usuarios/<int:pk>/suspender/", views.usuario_suspender, name="usuario_suspender"),
    path("usuarios/<int:pk>/eliminar/", views.usuario_eliminar, name="usuario_eliminar"),
    path("usuarios/<int:pk>/rol/", views.usuario_cambiar_rol, name="usuario_cambiar_rol"),
    path("roles/", views.roles, name="roles"),
    path("parametros/", views.parametros_globales, name="parametros"),
    path("moderacion/", views.moderacion, name="moderacion"),
    path("moderacion/obra/<int:pk>/restringir/", views.obra_restringir, name="obra_restringir"),
    path("moderacion/subasta/<int:pk>/pujas/", views.subasta_suspender_pujas, name="subasta_suspender_pujas"),
]
