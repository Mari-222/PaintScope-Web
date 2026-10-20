from datetime import datetime

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from obras.models import Obra
from subastas.models import Subasta
from usuarios.decorators import rol_requerido

from . import services
from .models import Visita


def _obra_exhibible(pk):
    """Precondición de CU-07: la obra está disponible para exhibición."""
    obra = get_object_or_404(Obra, pk=pk, restringida=False)
    en_exhibicion = obra.subastas.filter(
        estado__in=[Subasta.Estado.PROGRAMADA, Subasta.Estado.ACTIVA]).first()
    return obra, en_exhibicion


@rol_requerido("comprador")
def agendar(request, obra_id):
    obra, subasta = _obra_exhibible(obra_id)
    if not subasta:
        messages.error(request, "Esta obra ya no está disponible para visitas.")
        return redirect("subastas:explorar")
    tipo = request.GET.get("tipo", request.POST.get("tipo", Visita.Tipo.PRESENCIAL))
    if tipo not in Visita.Tipo.values:
        tipo = Visita.Tipo.PRESENCIAL

    if request.method == "POST":
        try:
            fecha = timezone.make_aware(datetime.strptime(request.POST.get("horario", ""), "%Y-%m-%dT%H:%M"))
            services.agendar(obra, request.user, tipo, fecha)
        except (ValueError, TypeError):
            messages.error(request, "Elige un horario de la lista.")
        except services.HorarioNoDisponible as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Visita agendada. Te enviamos la confirmación a tus notificaciones.")
            return redirect("visitas:mis_visitas")

    libres = services.horarios_disponibles(obra, tipo)
    sugeridas = {} if libres else services.sugerir_otras_fechas(obra, tipo)
    return render(request, "visitas/agendar.html", {
        "obra": obra, "subasta": subasta, "tipo": tipo, "tipos": Visita.Tipo.choices,
        "libres": libres, "sugeridas": sugeridas,
    })


@rol_requerido("comprador")
def mis_visitas(request):
    """Historial de visitas del comprador (poscondición de CU-07)."""
    visitas = request.user.visitas.select_related("obra__artista")
    return render(request, "visitas/mis_visitas.html", {"visitas": visitas, "ahora": timezone.now()})


@rol_requerido("comprador")
@require_POST
def cancelar(request, pk):
    visita = get_object_or_404(Visita, pk=pk, comprador=request.user, estado=Visita.Estado.AGENDADA)
    visita.estado = Visita.Estado.CANCELADA
    visita.save(update_fields=["estado"])
    messages.success(request, "Visita cancelada.")
    return redirect("visitas:mis_visitas")
