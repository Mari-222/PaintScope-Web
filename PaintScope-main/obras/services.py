from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from notificaciones.servicio import notificar
from subastas.services import crear_subasta
from usuarios.models import Usuario

from .models import Obra, Postulacion


class PostulacionInvalida(Exception):
    pass


@transaction.atomic
def postular(obra, evento):
    """CU-04: envía la obra a evaluación. Falla si la convocatoria ya cerró."""
    if obra.estado != Obra.Estado.BORRADOR:
        raise PostulacionInvalida("Solo las obras en borrador se pueden postular.")
    if not evento.convocatoria_abierta:
        raise PostulacionInvalida("La convocatoria de este evento ya cerró.")
    postulacion = Postulacion.objects.create(obra=obra, evento=evento)
    obra.estado = Obra.Estado.PENDIENTE
    obra.motivo_rechazo = ""
    obra.save(update_fields=["estado", "motivo_rechazo", "actualizada"])
    for curador in Usuario.objects.filter(rol=Usuario.Rol.CURADOR, is_active=True):
        notificar(curador, "postulacion", "Nueva postulación por evaluar",
                  f"«{obra.titulo}» de {obra.artista.nombre_visible} se postuló a {evento.nombre}.",
                  reverse("obras:evaluar", args=[postulacion.pk]))
    return postulacion


@transaction.atomic
def aprobar(postulacion, curador, precio_base):
    """CU-05 (aprobación): fija precio base y abre la subasta en el evento."""
    obra = postulacion.obra
    obra.precio_base = precio_base
    obra.curador = curador
    obra.estado = Obra.Estado.APROBADA
    obra.motivo_rechazo = ""
    obra.save()
    postulacion.estado = Postulacion.Estado.APROBADA
    postulacion.curador = curador
    postulacion.resuelta = timezone.now()
    postulacion.save()
    subasta = crear_subasta(obra, postulacion.evento)
    notificar(obra.artista, "obra_aprobada", "Tu obra fue aprobada",
              f"«{obra.titulo}» salió a subasta con precio base de ${precio_base:,.0f} en {postulacion.evento.nombre}.",
              reverse("subastas:detalle", args=[subasta.pk]))
    return subasta


@transaction.atomic
def rechazar(postulacion, curador, motivo):
    """CU-05 (rechazo): la obra vuelve a Borrador y el artista recibe el motivo."""
    obra = postulacion.obra
    obra.estado = Obra.Estado.BORRADOR
    obra.motivo_rechazo = motivo
    obra.curador = curador
    obra.save()
    postulacion.estado = Postulacion.Estado.RECHAZADA
    postulacion.curador = curador
    postulacion.motivo = motivo
    postulacion.resuelta = timezone.now()
    postulacion.save()
    notificar(obra.artista, "obra_rechazada", "Tu obra no fue aprobada",
              f"«{obra.titulo}»: {motivo}", reverse("obras:portafolio"))
