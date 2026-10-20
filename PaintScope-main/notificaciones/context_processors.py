def notificaciones(request):
    """Cantidad de avisos sin leer para la campana del encabezado."""
    if request.user.is_authenticated:
        return {"sin_leer": request.user.notificaciones.filter(leida=False).count()}
    return {"sin_leer": 0}
