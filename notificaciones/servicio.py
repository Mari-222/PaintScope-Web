from .models import Notificacion


def notificar(usuario, tipo, titulo, mensaje, url=""):
    """Crea una notificación dentro de la app para un usuario."""
    return Notificacion.objects.create(
        usuario=usuario, tipo=tipo, titulo=titulo[:120], mensaje=mensaje[:300], url=url
    )
