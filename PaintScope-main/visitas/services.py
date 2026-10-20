"""Horarios de visita (CU-07). La agenda se define con parámetros globales."""
from datetime import datetime, time, timedelta

from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from notificaciones.servicio import notificar
from panel import parametros

from .models import Visita


class HorarioNoDisponible(Exception):
    pass


def _franjas(desde_dia):
    """Todas las franjas teóricas de un día, de una hora cada una."""
    zona = timezone.get_current_timezone()
    inicio = parametros.obtener("visitas_hora_inicio")
    fin = parametros.obtener("visitas_hora_fin")
    for hora in range(inicio, fin):
        yield timezone.make_aware(datetime.combine(desde_dia, time(hour=hora)), zona)


def horarios_disponibles(obra, tipo, desde=None, dias=None):
    """
    Franjas libres de una obra, agrupadas por día: {fecha: [datetime, ...]}.
    Una franja está ocupada si ya hay una visita agendada de esa obra a esa hora
    (o del mismo tipo virtual/presencial para no cruzar guías).
    """
    ahora = timezone.now()
    desde = desde or timezone.localdate()
    dias = dias or parametros.obtener("visitas_dias_adelante")
    limite = desde + timedelta(days=dias)
    ocupadas = set(
        Visita.objects.filter(obra=obra, tipo=tipo, estado=Visita.Estado.AGENDADA,
                              fecha_hora__date__gte=desde, fecha_hora__date__lt=limite)
        .values_list("fecha_hora", flat=True)
    )
    libres = {}
    for n in range(dias):
        dia = desde + timedelta(days=n)
        franjas = [f for f in _franjas(dia) if f > ahora and f not in ocupadas]
        if franjas:
            libres[dia] = franjas
    return libres


def sugerir_otras_fechas(obra, tipo):
    """Si no hay horarios en la agenda normal, busca en las dos semanas siguientes."""
    dias = parametros.obtener("visitas_dias_adelante")
    desde = timezone.localdate() + timedelta(days=dias)
    return horarios_disponibles(obra, tipo, desde=desde, dias=14)


@transaction.atomic
def agendar(obra, comprador, tipo, fecha_hora):
    """Registra la visita si la franja sigue libre y avisa al comprador y al artista."""
    libres = horarios_disponibles(obra, tipo)
    todas = [f for franjas in libres.values() for f in franjas]
    if fecha_hora not in todas:
        raise HorarioNoDisponible("Ese horario ya no está disponible. Elige otro.")
    visita = Visita.objects.create(obra=obra, comprador=comprador, tipo=tipo, fecha_hora=fecha_hora)
    local = timezone.localtime(fecha_hora)
    notificar(comprador, "visita", "Visita confirmada",
              f"Tu visita {visita.get_tipo_display().lower()} a «{obra.titulo}» es el {local:%d/%m} a las {local:%H:%M}.",
              reverse("visitas:mis_visitas"))
    notificar(obra.artista, "visita", "Agendaron una visita a tu obra",
              f"{comprador.nombre_visible} visitará «{obra.titulo}» el {local:%d/%m} a las {local:%H:%M}.",
              reverse("obras:portafolio"))
    return visita
