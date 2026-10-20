from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from subastas.models import Subasta
from subastas.services import crear_subasta, ventas_exitosas
from usuarios.decorators import rol_requerido
from usuarios.models import Usuario

from . import services
from .forms import EvaluacionForm, EventoForm, ObraForm, PostulacionForm
from .models import Evento, Obra, Postulacion


# ----------------------------------------------------------------- artista
@rol_requerido("artista")
def portafolio(request):
    """Mi portafolio (prototipo: pestañas «Todas las obras» y «Borradores»)."""
    pestana = request.GET.get("ver", "todas")
    obras = request.user.obras.all()
    if pestana == "borradores":
        obras = obras.filter(estado=Obra.Estado.BORRADOR)
    return render(request, "obras/portafolio.html", {
        "obras": obras, "pestana": pestana,
        "total": request.user.obras.count(),
        "borradores": request.user.obras.filter(estado=Obra.Estado.BORRADOR).count(),
    })


@rol_requerido("artista")
def obra_nueva(request):
    """CU-03: cargar una obra; se guarda como Borrador."""
    form = ObraForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        obra = form.save(commit=False)
        obra.artista = request.user
        obra.estado = Obra.Estado.BORRADOR
        obra.save()
        messages.success(request, "Obra guardada como borrador. Ya puedes postularla a un evento.")
        return redirect("obras:postular", pk=obra.pk)
    return render(request, "obras/obra_form.html", {"form": form, "titulo": "Añadir una obra"})


@rol_requerido("artista")
def obra_editar(request, pk):
    obra = get_object_or_404(Obra, pk=pk, artista=request.user)
    if not obra.editable:
        messages.error(request, "Solo puedes editar obras en borrador.")
        return redirect("obras:portafolio")
    form = ObraForm(request.POST or None, request.FILES or None, instance=obra)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Cambios guardados.")
        return redirect("obras:portafolio")
    return render(request, "obras/obra_form.html", {"form": form, "titulo": "Editar obra", "obra": obra})


@rol_requerido("artista")
@require_POST
def obra_eliminar(request, pk):
    obra = get_object_or_404(Obra, pk=pk, artista=request.user)
    if not obra.editable:
        messages.error(request, "Solo puedes eliminar obras en borrador.")
    else:
        obra.delete()
        messages.success(request, "Borrador eliminado.")
    return redirect("obras:portafolio")


@rol_requerido("artista")
def postular(request, pk):
    """CU-04: elegir evento y enviar la postulación al curador."""
    obra = get_object_or_404(Obra, pk=pk, artista=request.user)
    if obra.estado != Obra.Estado.BORRADOR:
        messages.error(request, "Esta obra ya fue postulada.")
        return redirect("obras:mis_postulaciones")
    form = PostulacionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.postular(obra, form.cleaned_data["evento"])
        except services.PostulacionInvalida as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Postulación enviada. El curador la revisará pronto.")
            return redirect("obras:mis_postulaciones")
    eventos = Evento.objects.filter(publicado=True).order_by("cierre_convocatoria")
    return render(request, "obras/postular.html", {"obra": obra, "form": form, "eventos": eventos})


@rol_requerido("artista")
def mis_postulaciones(request):
    postulaciones = Postulacion.objects.filter(obra__artista=request.user).select_related("obra", "evento")
    return render(request, "obras/mis_postulaciones.html", {"postulaciones": postulaciones})


# ----------------------------------------------------------------- curador
@rol_requerido("curador", "admin")
def postulaciones(request):
    """Panel de revisión: postulaciones por evaluar y ya resueltas."""
    estado = request.GET.get("estado", "pendiente")
    items = Postulacion.objects.select_related("obra__artista", "evento")
    if estado in ("pendiente", "aprobada", "rechazada"):
        items = items.filter(estado=estado)
    conteos = dict(Postulacion.objects.values_list("estado").annotate(n=Count("id")))
    return render(request, "obras/postulaciones.html", {
        "items": items, "estado": estado, "conteos": conteos,
    })


@rol_requerido("curador", "admin")
def evaluar(request, pk):
    """CU-05: revisar la obra, aprobar con precio base o rechazar con motivo."""
    postulacion = get_object_or_404(Postulacion.objects.select_related("obra__artista", "evento"), pk=pk)
    if postulacion.estado != Postulacion.Estado.PENDIENTE:
        messages.info(request, "Esta postulación ya fue evaluada.")
        return redirect("obras:postulaciones")
    form = EvaluacionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if form.cleaned_data["decision"] == "aprobar":
            services.aprobar(postulacion, request.user, form.cleaned_data["precio_base"])
            messages.success(request, "Obra aprobada. La subasta quedó creada y el artista fue notificado.")
        else:
            services.rechazar(postulacion, request.user, form.cleaned_data["motivo"].strip())
            messages.success(request, "Obra rechazada. El artista recibió el motivo.")
        return redirect("obras:postulaciones")
    return render(request, "obras/evaluar.html", {"p": postulacion, "obra": postulacion.obra, "form": form})


# ----------------------------------------------------------------- eventos
@rol_requerido("curador", "admin")
def eventos(request):
    return render(request, "obras/eventos.html", {
        "eventos": Evento.objects.annotate(n_subastas=Count("subastas")),
    })


@rol_requerido("curador", "admin")
def evento_nuevo(request):
    form = EventoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        evento = form.save(commit=False)
        evento.creado_por = request.user
        evento.save()
        messages.success(request, "Evento creado. Publícalo cuando esté listo para recibir postulaciones.")
        return redirect("obras:evento_detalle", pk=evento.pk)
    return render(request, "obras/evento_form.html", {"form": form, "titulo": "Crear evento temático"})


@rol_requerido("curador", "admin")
def evento_editar(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    form = EventoForm(request.POST or None, instance=evento)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Evento actualizado.")
        return redirect("obras:evento_detalle", pk=evento.pk)
    return render(request, "obras/evento_form.html", {"form": form, "titulo": "Editar evento", "evento": evento})


@rol_requerido("curador", "admin")
def evento_detalle(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    disponibles = Obra.objects.filter(estado=Obra.Estado.APROBADA, restringida=False).select_related("artista")
    return render(request, "obras/evento_detalle.html", {
        "evento": evento,
        "subastas": evento.subastas.select_related("obra__artista"),
        "disponibles": disponibles,
    })


@rol_requerido("curador", "admin")
@require_POST
def evento_publicar(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    evento.publicado = not evento.publicado
    evento.save(update_fields=["publicado"])
    messages.success(request, "Evento publicado." if evento.publicado else "Evento pasó a borrador.")
    return redirect("obras:evento_detalle", pk=pk)


@rol_requerido("curador", "admin")
@require_POST
def evento_incluir_obra(request, pk):
    """RF-07: asociar una obra aprobada a un evento publicado."""
    evento = get_object_or_404(Evento, pk=pk)
    obra = get_object_or_404(Obra, pk=request.POST.get("obra"), estado=Obra.Estado.APROBADA)
    if not evento.publicado:
        messages.error(request, "Publica el evento antes de asociarle obras.")
    elif evento.fecha_fin <= timezone.now():
        messages.error(request, "El evento ya terminó.")
    else:
        crear_subasta(obra, evento)
        messages.success(request, f"«{obra.titulo}» se incluyó en {evento.nombre}.")
    return redirect("obras:evento_detalle", pk=pk)


# ----------------------------------------------------------------- artistas
def artistas(request):
    if not request.user.is_authenticated:
        return redirect("login")
    lista = (Usuario.objects.filter(rol=Usuario.Rol.ARTISTA, is_active=True)
             .annotate(n_obras=Count("obras", filter=~Q(obras__estado=Obra.Estado.BORRADOR)))
             .order_by("-insignia_verificado", "first_name"))
    return render(request, "obras/artistas.html", {"artistas": lista})


def perfil_artista(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    artista = get_object_or_404(Usuario, pk=pk, rol=Usuario.Rol.ARTISTA)
    subastas = (Subasta.objects.filter(obra__artista=artista, obra__restringida=False)
                .exclude(estado=Subasta.Estado.CERRADA).select_related("obra__artista")
                .annotate(n_pujas=Count("pujas")))
    return render(request, "obras/perfil_artista.html", {
        "artista": artista,
        "subastas": subastas,
        "n_obras": artista.obras.exclude(estado=Obra.Estado.BORRADOR).count(),
        "n_vendidas": ventas_exitosas(artista),
    })
