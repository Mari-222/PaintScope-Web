from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.urls import reverse

from notificaciones.servicio import notificar
from obras.models import Obra, Postulacion
from subastas.models import Subasta
from usuarios.decorators import rol_requerido
from usuarios.models import Usuario

from .forms import ParametrosForm, UsuarioPanelForm

# Matriz de permisos que muestra la pantalla «Roles y permisos» (RF-15)
PERMISOS = [
    ("Cargar obras y postularlas a eventos", {"artista": True}),
    ("Evaluar postulaciones y definir precio base", {"curador": True}),
    ("Crear y publicar eventos temáticos", {"curador": True, "admin": True}),
    ("Pujar en subastas", {"comprador": True, "artista": True}),
    ("Agendar visitas guiadas", {"comprador": True}),
    ("Registrar método de pago", {"comprador": True, "artista": True}),
    ("Gestionar usuarios, roles y parámetros", {"admin": True}),
    ("Moderar obras y suspender pujas", {"admin": True}),
]

@rol_requerido("admin")
def inicio(request):
    return render(request, "panel/inicio.html", {
        "usuarios_activos": Usuario.objects.filter(is_active=True).count(),
        "suspendidos": Usuario.objects.filter(is_active=False).count(),
        "obras": Obra.objects.count(),
        "activas": Subasta.objects.filter(estado=Subasta.Estado.ACTIVA).count(),
        "pendientes": Postulacion.objects.filter(estado=Postulacion.Estado.PENDIENTE).count(),
        "por_rol": dict(Usuario.objects.values_list("rol").annotate(n=Count("id"))),
    })


# ----------------------------------------------------------------- usuarios
def _actividad_activa(usuario):
    """CU-08 (alternativo): subastas o postulaciones en curso del usuario."""
    return (
        Subasta.objects.filter(obra__artista=usuario, estado__in=["programada", "activa"]).exists()
        or Postulacion.objects.filter(obra__artista=usuario, estado="pendiente").exists()
        or Subasta.objects.filter(estado="activa", pujas__comprador=usuario).exists()
    )


@rol_requerido("admin")
def usuarios(request):
    q = request.GET.get("q", "").strip()
    rol = request.GET.get("rol", "")
    lista = Usuario.objects.all().order_by("first_name", "email")
    if q:
        lista = lista.filter(Q(email__icontains=q) | Q(first_name__icontains=q))
    if rol in Usuario.Rol.values:
        lista = lista.filter(rol=rol)
    return render(request, "panel/usuarios.html", {
        "usuarios": lista, "q": q, "rol": rol, "roles": Usuario.Rol.choices,
    })


@rol_requerido("admin")
def usuario_nuevo(request):
    form = UsuarioPanelForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Usuario creado.")
        return redirect("panel:usuarios")
    return render(request, "panel/usuario_form.html", {"form": form, "titulo": "Crear usuario"})


@rol_requerido("admin")
def usuario_editar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    form = UsuarioPanelForm(request.POST or None, instance=usuario)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Cambios guardados.")
        return redirect("panel:usuarios")
    return render(request, "panel/usuario_form.html", {"form": form, "titulo": "Editar usuario", "u": usuario})


@rol_requerido("admin")
@require_POST
def usuario_suspender(request, pk):
    """Suspende o reactiva una cuenta (is_active). Un administrador no se suspende a sí mismo."""
    usuario = get_object_or_404(Usuario, pk=pk)
    if usuario.pk == request.user.pk:
        messages.error(request, "No puedes suspender tu propia cuenta.")
        return redirect("panel:usuarios")
    if usuario.is_active and _actividad_activa(usuario) and request.POST.get("confirmar") != "1":
        return render(request, "panel/confirmar_usuario.html", {"u": usuario, "accion": "suspender"})
    usuario.is_active = not usuario.is_active
    usuario.save(update_fields=["is_active"])
    messages.success(request, "Cuenta reactivada." if usuario.is_active else "Cuenta suspendida.")
    return redirect("panel:usuarios")


@rol_requerido("admin")
def usuario_eliminar(request, pk):
    """Elimina un usuario; con actividad activa pide una confirmación adicional (CU-08)."""
    usuario = get_object_or_404(Usuario, pk=pk)
    if usuario.pk == request.user.pk:
        messages.error(request, "No puedes eliminar tu propia cuenta.")
        return redirect("panel:usuarios")
    activa = _actividad_activa(usuario)
    if request.method == "POST":
        if activa and request.POST.get("confirmar") != "1":
            messages.error(request, "Confirma que quieres eliminar un usuario con actividad en curso.")
        else:
            usuario.delete()
            messages.success(request, "Usuario eliminado.")
            return redirect("panel:usuarios")
    return render(request, "panel/confirmar_usuario.html", {"u": usuario, "accion": "eliminar", "activa": activa})


@rol_requerido("admin")
@require_POST
def usuario_cambiar_rol(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    nuevo = request.POST.get("rol")
    if nuevo not in Usuario.Rol.values:
        messages.error(request, "Elige un rol válido.")
    elif usuario.pk == request.user.pk and nuevo != Usuario.Rol.ADMIN:
        messages.error(request, "No puedes quitarte el rol de administrador a ti mismo.")
    else:
        usuario.rol = nuevo
        usuario.is_staff = nuevo == Usuario.Rol.ADMIN or usuario.is_superuser
        usuario.save(update_fields=["rol", "is_staff"])
        messages.success(request, f"{usuario.nombre_visible} ahora es {usuario.get_rol_display()}.")
    return redirect("panel:usuarios")


# ------------------------------------------------------------ roles y parámetros
@rol_requerido("admin")
def roles(request):
    conteos = dict(Usuario.objects.values_list("rol").annotate(n=Count("id")))
    columnas = [(valor, nombre, conteos.get(valor, 0)) for valor, nombre in Usuario.Rol.choices]
    filas = [(texto, [permisos.get(valor, False) for valor, _, _ in columnas]) for texto, permisos in PERMISOS]
    return render(request, "panel/roles.html", {"columnas": columnas, "filas": filas})


@rol_requerido("admin")
def parametros_globales(request):
    form = ParametrosForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.guardar()
        messages.success(request, "Parámetros guardados.")
        return redirect("panel:parametros")
    return render(request, "panel/parametros.html", {"form": form})


# ----------------------------------------------------------------- moderación
@rol_requerido("admin")
def moderacion(request):
    filtro = request.GET.get("f", "Todas")
    obras = Obra.objects.exclude(estado=Obra.Estado.BORRADOR).select_related("artista")
    if filtro == "Restringidas":
        obras = obras.filter(restringida=True)
    elif filtro == "Pujas suspendidas":
        obras = obras.filter(subastas__pujas_suspendidas=True,
                             subastas__estado__in=["programada", "activa"]).distinct()
    filas = []
    for obra in obras:
        abierta = obra.subastas.filter(estado__in=["programada", "activa"]).first()
        filas.append({"obra": obra, "subasta": abierta})
    return render(request, "panel/moderacion.html", {
        "filas": filas, "filtro": filtro, "filtros": ["Todas", "Restringidas", "Pujas suspendidas"],
    })


@rol_requerido("admin")
@require_POST
def obra_restringir(request, pk):
    """Retira (o devuelve) una obra del catálogo: equivale a «Eliminar obra del catálogo» de la ERS."""
    obra = get_object_or_404(Obra, pk=pk)
    obra.restringida = not obra.restringida
    obra.save(update_fields=["restringida", "actualizada"])
    messages.success(request, "Obra retirada del catálogo." if obra.restringida else "Obra restaurada en el catálogo.")
    return redirect(request.POST.get("next") or "panel:moderacion")


@rol_requerido("admin")
@require_POST
def subasta_suspender_pujas(request, pk):
    subasta = get_object_or_404(Subasta, pk=pk)
    subasta.pujas_suspendidas = not subasta.pujas_suspendidas
    subasta.save(update_fields=["pujas_suspendidas"])
    messages.success(request, "Pujas suspendidas." if subasta.pujas_suspendidas else "Pujas reanudadas.")
    return redirect("panel:moderacion")

@rol_requerido("admin")
@require_POST
def usuario_verificar(request, pk):
    """El administrador otorga o quita la insignia de verificado a un artista."""
    artista = get_object_or_404(Usuario, pk=pk, rol=Usuario.Rol.ARTISTA)
    artista.insignia_verificado = not artista.insignia_verificado
    artista.save(update_fields=["insignia_verificado"])
    if artista.insignia_verificado:
        notificar(artista, "sistema", "Ya eres artista verificado",
                  "Un administrador verificó tu perfil. Ahora tu perfil y tus obras llevan el sello de Verificado.",
                  reverse("obras:perfil_artista", args=[artista.pk]))
        messages.success(request, f"{artista.nombre_visible} ahora es artista verificado.")
    else:
        messages.success(request, f"Se quitó la insignia de verificado a {artista.nombre_visible}.")
    return redirect("panel:usuarios")
