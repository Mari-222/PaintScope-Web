from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CambioPasswordForm, MetodoPagoForm, PerfilForm, RegistroForm
from .models import Usuario


def destino_por_rol(usuario):
    """Nombre de la ruta del panel principal de cada rol (CU-02, paso 3)."""
    if usuario.es_admin:
        return "panel:inicio"
    return {
        Usuario.Rol.ARTISTA: "obras:portafolio",
        Usuario.Rol.CURADOR: "obras:postulaciones",
        Usuario.Rol.COMPRADOR: "subastas:explorar",
    }.get(usuario.rol, "perfil")


def inicio(request):
    """Raíz del sitio: al panel del rol si hay sesión, si no al inicio de sesión."""
    if request.user.is_authenticated:
        return redirect(destino_por_rol(request.user))
    return redirect("login")


def sin_permiso(request, exception=None):
    return render(request, "403.html", status=403)


def registro_view(request):
    if request.user.is_authenticated:
        return redirect(destino_por_rol(request.user))
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        return redirect(destino_por_rol(usuario))
    return render(request, "usuarios/registro.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect(destino_por_rol(request.user))
    suspendida = False
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            usuario = form.get_user()
            login(request, usuario)
            destino = request.GET.get("next")
            if destino and destino.startswith("/") and not destino.startswith("//"):
                return redirect(destino)
            return redirect(destino_por_rol(usuario))
        correo = request.POST.get("username", "").strip().lower()
        suspendida = Usuario.objects.filter(email__iexact=correo, is_active=False).exists()
    else:
        form = AuthenticationForm()
    return render(request, "usuarios/login.html", {"form": form, "suspendida": suspendida})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def perfil_view(request):
    """Ver y editar datos personales (RF-03), contraseña y método de pago (RF-16)."""
    usuario = request.user
    form = PerfilForm(request.POST or None, instance=usuario, prefix="perfil")
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Tus datos se guardaron.")
        return redirect("perfil")
    contexto = {
        "form": form,
        "form_password": CambioPasswordForm(usuario),
        "form_pago": MetodoPagoForm(),
        "metodos": usuario.metodos_pago.all() if usuario.puede_pujar else [],
        "resumen": _resumen_por_rol(usuario),
    }
    return render(request, "usuarios/perfil.html", contexto)


@login_required
@require_POST
def cambiar_password(request):
    form = CambioPasswordForm(request.user, request.POST)
    if form.is_valid():
        usuario = form.save()
        update_session_auth_hash(request, usuario)  # no cierra la sesión actual
        messages.success(request, "Tu contraseña se actualizó.")
        return redirect("perfil")
    contexto = {
        "form": PerfilForm(instance=request.user, prefix="perfil"),
        "form_password": form,
        "form_pago": MetodoPagoForm(),
        "metodos": request.user.metodos_pago.all() if request.user.puede_pujar else [],
        "resumen": _resumen_por_rol(request.user),
        "abrir_password": True,
    }
    return render(request, "usuarios/perfil.html", contexto)


@login_required
@require_POST
def agregar_metodo_pago(request):
    if not request.user.puede_pujar:
        messages.error(request, "Tu rol no registra método de pago.")
        return redirect("perfil")
    form = MetodoPagoForm(request.POST)
    if form.is_valid():
        form.guardar(request.user)
        messages.success(request, "Método de pago registrado. Ya puedes pujar.")
        destino = request.POST.get("next", "")
        if destino.startswith("/") and not destino.startswith("//"):
            return redirect(destino)
        return redirect("perfil")
    contexto = {
        "form": PerfilForm(instance=request.user, prefix="perfil"),
        "form_password": CambioPasswordForm(request.user),
        "form_pago": form,
        "metodos": request.user.metodos_pago.all(),
        "resumen": _resumen_por_rol(request.user),
        "abrir_pago": True,
    }
    return render(request, "usuarios/perfil.html", contexto)


@login_required
@require_POST
def eliminar_metodo_pago(request, pk):
    metodo = get_object_or_404(request.user.metodos_pago, pk=pk)
    metodo.delete()
    messages.success(request, "Método de pago eliminado.")
    return redirect("perfil")


def _resumen_por_rol(usuario):
    """Tarjetas de resumen del perfil según el rol (como en el prototipo)."""
    from obras.models import Obra, Postulacion
    from subastas.models import Puja, Subasta
    from visitas.models import Visita

    if usuario.es_admin:
        return [
            ("Usuarios activos", Usuario.objects.filter(is_active=True).count()),
            ("Obras en la plataforma", Obra.objects.count()),
            ("Subastas activas", Subasta.objects.filter(estado=Subasta.Estado.ACTIVA).count()),
        ]
    if usuario.es_artista:
        return [
            ("Obras en portafolio", Obra.objects.filter(artista=usuario).count()),
            ("Obras vendidas", Subasta.objects.filter(obra__artista=usuario, ganador__isnull=False).count()),
            ("Postulaciones", Postulacion.objects.filter(obra__artista=usuario).count()),
        ]
    if usuario.es_curador:
        return [
            ("Postulaciones por evaluar", Postulacion.objects.filter(estado=Postulacion.Estado.PENDIENTE).count()),
            ("Piezas aprobadas por mí", Obra.objects.filter(curador=usuario).count()),
        ]
    return [
        ("Subastas con puja", Puja.objects.filter(comprador=usuario).values("subasta").distinct().count()),
        ("Subastas ganadas", Subasta.objects.filter(ganador=usuario).count()),
        ("Visitas agendadas", Visita.objects.filter(comprador=usuario, estado=Visita.Estado.AGENDADA).count()),
    ]