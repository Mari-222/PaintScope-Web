from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST


@login_required
def lista(request):
    items = request.user.notificaciones.all()[:100]
    return render(request, "notificaciones/lista.html", {"items": items})


@login_required
@require_POST
def marcar_todas(request):
    request.user.notificaciones.filter(leida=False).update(leida=True)
    return redirect("notificaciones:lista")


@login_required
def abrir(request, pk):
    """Marca la notificación como leída y lleva al usuario a lo que avisa."""
    aviso = get_object_or_404(request.user.notificaciones, pk=pk)
    if not aviso.leida:
        aviso.leida = True
        aviso.save(update_fields=["leida"])
    return redirect(aviso.url or "notificaciones:lista")
