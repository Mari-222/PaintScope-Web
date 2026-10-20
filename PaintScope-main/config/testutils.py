"""Fábricas compartidas por las pruebas de todas las apps."""
import io
from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from obras.models import Evento, Obra
from obras import services as obras_services
from usuarios.models import MetodoPago, Usuario

CLAVE = "Clave-segura-123"


def usuario(rol="comprador", email=None, nombre=None, con_pago=False, **extra):
    email = email or f"{rol}{Usuario.objects.count()}@test.cr"
    u = Usuario.objects.create_user(email=email, password=CLAVE, first_name=nombre or rol.capitalize(),
                                    rol=rol, is_staff=(rol == "admin"), **extra)
    if con_pago:
        MetodoPago.objects.create(usuario=u, titular=u.first_name, ultimos4="4242", vencimiento="12/39")
    return u


def imagen(nombre="obra.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (40, 30), "#c96d4a").save(buffer, "PNG")
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type="image/png")


def evento(publicado=True, abierta=True, **extra):
    ahora = timezone.now()
    datos = dict(nombre="Artistas Locales", tematica="Arte local", temporada="Todo el año",
                 fecha_inicio=ahora - timedelta(hours=1), fecha_fin=ahora + timedelta(days=7),
                 cierre_convocatoria=ahora + timedelta(days=3) if abierta else ahora - timedelta(hours=2),
                 publicado=publicado)
    datos.update(extra)
    return Evento.objects.create(**datos)


def obra(artista, **extra):
    datos = dict(titulo="Costa quieta", descripcion="Óleo de la costa.", tecnica="Óleo sobre lienzo",
                 categoria="Paisaje", dimensiones="90 × 120 cm", anio=2024, imagen_url="https://example.com/a.jpg")
    datos.update(extra)
    return Obra.objects.create(artista=artista, **datos)


def subasta_activa(artista=None, curador=None, base=500, evt=None, **extra):
    """Crea una obra, la postula, la aprueba y devuelve su subasta ya activa."""
    artista = artista or usuario("artista")
    curador = curador or usuario("curador")
    evt = evt or evento()
    o = obra(artista, **extra)
    post = obras_services.postular(o, evt)
    return obras_services.aprobar(post, curador, Decimal(base))
