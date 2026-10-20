from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def rol_requerido(*roles):
    """
    Restringe una vista a ciertos roles (RF-02). El administrador siempre pasa
    en las vistas del panel; en el resto debe figurar en `roles`.
    Uso: @rol_requerido("artista") o @rol_requerido("curador", "admin").
    """

    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(request, *args, **kwargs):
            usuario = request.user
            permitido = usuario.rol in roles or ("admin" in roles and usuario.es_admin)
            if not permitido:
                raise PermissionDenied
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador
