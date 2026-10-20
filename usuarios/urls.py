from django.urls import path

from . import views

urlpatterns = [
    path("registro/", views.registro_view, name="registro"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("perfil/", views.perfil_view, name="perfil"),
    path("perfil/password/", views.cambiar_password, name="cambiar_password"),
    path("perfil/pago/", views.agregar_metodo_pago, name="agregar_metodo_pago"),
    path("perfil/pago/<int:pk>/eliminar/", views.eliminar_metodo_pago, name="eliminar_metodo_pago"),
]
