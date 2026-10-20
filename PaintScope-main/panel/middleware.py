from django.shortcuts import render

from . import parametros

RUTAS_LIBRES = ("/static/", "/media/", "/admin/", "/usuarios/login/", "/usuarios/logout/")


class MantenimientoMiddleware:
    """Si el modo mantenimiento está activo, solo los administradores navegan."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(RUTAS_LIBRES):
            try:
                activo = parametros.obtener("modo_mantenimiento")
            except Exception:  # base aún sin migrar
                activo = False
            usuario = request.user
            es_admin = usuario.is_authenticated and getattr(usuario, "es_admin", False)
            if activo and not es_admin:
                return render(request, "mantenimiento.html", status=503)
        return self.get_response(request)
