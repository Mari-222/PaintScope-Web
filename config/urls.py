"""Rutas principales de PaintScope."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from usuarios.views import inicio

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", inicio, name="inicio"),
    path("usuarios/", include("usuarios.urls")),
    path("obras/", include("obras.urls")),
    path("subastas/", include("subastas.urls")),
    path("visitas/", include("visitas.urls")),
    path("notificaciones/", include("notificaciones.urls")),
    path("panel/", include("panel.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "usuarios.views.sin_permiso"
