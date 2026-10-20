from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from obras.models import Obra
from usuarios.decorators import rol_requerido

from . import services
from .models import Puja, Subasta

FILTROS = ["Todas", "Óleo", "Acuarela", "Acrílico", "Paisaje", "Retrato", "Abstracto", "Terminan pronto"]


def _visibles():
    """Subastas que se muestran en el catálogo: abiertas o por abrir, y no restringidas."""
    return (Subasta.objects.filter(estado__in=[Subasta.Estado.PROGRAMADA, Subasta.Estado.ACTIVA],
                                   obra__restringida=False)
            .select_related("obra__artista", "evento")
            .annotate(n_pujas=Count("pujas")))


@rol_requerido("artista", "curador", "comprador", "admin")
def explorar(request):
    """Catálogo de obras en subasta con búsqueda y filtros (como «Explorar» del prototipo)."""
    services.sincronizar_estados()
    filtro = request.GET.get("f", "Todas")
    q = request.GET.get("q", "").strip()
    subastas = _visibles()
    if q:
        subastas = subastas.filter(
            Q(obra__titulo__icontains=q) | Q(obra__artista__first_name__icontains=q)
            | Q(obra__tecnica__icontains=q) | Q(obra__categoria__icontains=q)
        )
    if filtro in ("Óleo", "Acuarela", "Acrílico"):
        subastas = subastas.filter(obra__tecnica__startswith=filtro)
    elif filtro in ("Paisaje", "Retrato", "Abstracto"):
        subastas = subastas.filter(obra__categoria=filtro)
    elif filtro == "Terminan pronto":
        subastas = subastas.filter(estado=Subasta.Estado.ACTIVA).order_by("fecha_fin")
    return render(request, "subastas/explorar.html", {
        "subastas": subastas, "filtros": FILTROS, "filtro": filtro, "q": q,
    })


@rol_requerido("artista", "curador", "comprador", "admin")
def en_vivo(request):
    """RF-08: dashboard de subastas activas con puja más alta y tiempo restante."""
    services.sincronizar_estados()
    activas = _visibles().filter(estado=Subasta.Estado.ACTIVA).order_by("fecha_fin")
    return render(request, "subastas/en_vivo.html", {"subastas": activas})


@require_GET
@rol_requerido("artista", "curador", "comprador", "admin")
def api_dashboard(request):
    """Estado de todas las subastas activas; el dashboard lo consulta cada 2 s (RNF-03: ≤ 3 s)."""
    services.sincronizar_estados()
    activas = _visibles().filter(estado=Subasta.Estado.ACTIVA).order_by("fecha_fin")
    return JsonResponse({"subastas": [services.estado_para_json(s) for s in activas]})


@require_GET
@rol_requerido("artista", "curador", "comprador", "admin")
def api_estado(request, pk):
    services.sincronizar_estados()
    subasta = get_object_or_404(Subasta, pk=pk)
    return JsonResponse(services.estado_para_json(subasta))


@rol_requerido("artista", "curador", "comprador", "admin")
def detalle(request, pk):
    services.sincronizar_estados()
    subasta = get_object_or_404(Subasta.objects.select_related("obra__artista", "evento", "ganador"), pk=pk)
    if subasta.obra.restringida and not request.user.es_admin:
        messages.info(request, "Esta obra fue retirada del catálogo.")
        return redirect("subastas:explorar")
    usuario = request.user
    motivo_bloqueo = None
    if subasta.cerrada:
        motivo_bloqueo = "La subasta terminó."
    elif subasta.estado == Subasta.Estado.PROGRAMADA:
        motivo_bloqueo = "La subasta aún no abre."
    elif subasta.pujas_suspendidas:
        motivo_bloqueo = "Las pujas están suspendidas por moderación."
    elif usuario.es_comprador and not usuario.tiene_metodo_pago:
        motivo_bloqueo = "pago"
    historial = subasta.pujas.select_related("comprador")[:8]
    mi_puja = subasta.pujas.filter(comprador=usuario).first() if usuario.es_comprador else None
    return render(request, "subastas/detalle.html", {
        "s": subasta, "obra": subasta.obra, "historial": historial,
        "puede_pujar": usuario.es_comprador, "motivo_bloqueo": motivo_bloqueo,
        "lidera": bool(mi_puja and subasta.puja_ganadora and subasta.puja_ganadora.comprador_id == usuario.pk),
        "sugerida": subasta.monto_minimo + 49,
    })


@rol_requerido("comprador")
@require_POST
def pujar(request, pk):
    """CU-06: registra la puja o la rechaza con un mensaje claro."""
    try:
        puja = services.registrar_puja(pk, request.user, request.POST.get("monto", ""))
    except services.PujaRechazada as error:
        messages.error(request, str(error))
    else:
        if puja.extendida:
            messages.success(request, "Tu puja quedó registrada. Entró al final, así que el cierre se extendió.")
        else:
            messages.success(request, "Tu puja quedó registrada. ¡Vas liderando!")
    return redirect("subastas:detalle", pk=pk)


@rol_requerido("comprador")
def mis_pujas(request):
    """Prototipo: pestañas Ganando / Superado / Ganadas."""
    services.sincronizar_estados()
    usuario = request.user
    ids = Puja.objects.filter(comprador=usuario).values_list("subasta", flat=True).distinct()
    subastas = Subasta.objects.filter(pk__in=list(ids)).select_related("obra__artista")
    ganando, superado, ganadas = [], [], []
    for s in subastas:
        lider = s.puja_ganadora
        mi_mejor = s.pujas.filter(comprador=usuario).first()
        fila = {"s": s, "mi_puja": mi_mejor}
        if s.cerrada:
            if s.ganador_id == usuario.pk:
                ganadas.append(fila)
        elif lider and lider.comprador_id == usuario.pk:
            ganando.append(fila)
        else:
            superado.append(fila)
    pestana = request.GET.get("tab", "ganando")
    mostrar = {"ganando": ganando, "superado": superado, "ganadas": ganadas}.get(pestana, ganando)
    return render(request, "subastas/mis_pujas.html", {
        "pestana": pestana, "filas": mostrar,
        "conteos": {"ganando": len(ganando), "superado": len(superado), "ganadas": len(ganadas)},
    })
