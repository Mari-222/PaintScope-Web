"""Menú lateral y tema de color según el rol activo (corrección del profesor al prototipo)."""

# (etiqueta, icono, nombre de ruta, rutas que lo marcan como activo)
_EXPLORAR = ("Explorar", "compass", "subastas:explorar", ("subastas:explorar", "subastas:detalle"))
_ARTISTAS = ("Artistas", "artists", "obras:artistas", ("obras:artistas", "obras:perfil_artista"))
_AVISOS = ("Notificaciones", "bell", "notificaciones:lista", ("notificaciones:lista",))
_PERFIL = ("Mi perfil", "user", "perfil", ("perfil", "cambiar_password", "agregar_metodo_pago"))

MENUS = {
    "artista": [
        ("Mi portafolio", "palette", "obras:portafolio", ("obras:portafolio", "obras:obra_nueva", "obras:obra_editar", "obras:postular")),
        ("Mis postulaciones", "send", "obras:mis_postulaciones", ("obras:mis_postulaciones",)),
        ("Mis pujas", "gavel", "subastas:mis_pujas", ("subastas:mis_pujas",)),
        _EXPLORAR, _ARTISTAS, _AVISOS, _PERFIL,
    ],
    "comprador": [
        _EXPLORAR,
        ("Subastas en vivo", "live", "subastas:en_vivo", ("subastas:en_vivo",)),
        ("Mis pujas", "gavel", "subastas:mis_pujas", ("subastas:mis_pujas",)),
        ("Mis visitas", "calendar", "visitas:mis_visitas", ("visitas:mis_visitas", "visitas:agendar")),
        _ARTISTAS, _AVISOS, _PERFIL,
    ],
    "curador": [
        ("Postulaciones", "check", "obras:postulaciones", ("obras:postulaciones", "obras:evaluar")),
        ("Eventos temáticos", "calendar", "obras:eventos",
         ("obras:eventos", "obras:evento_nuevo", "obras:evento_detalle", "obras:evento_editar")),
        _EXPLORAR, _ARTISTAS, _AVISOS, _PERFIL,
    ],
    "admin": [
        ("Panel", "home", "panel:inicio", ("panel:inicio",)),
        ("Usuarios", "users", "panel:usuarios", ("panel:usuarios", "panel:usuario_nuevo", "panel:usuario_editar", "panel:usuario_eliminar", "panel:usuario_suspender")),
        ("Roles y permisos", "shield", "panel:roles", ("panel:roles",)),
        ("Parámetros", "sliders", "panel:parametros", ("panel:parametros",)),
        ("Moderación de obras", "compass", "panel:moderacion", ("panel:moderacion",)),
        ("Eventos temáticos", "calendar", "obras:eventos", ("obras:eventos", "obras:evento_nuevo", "obras:evento_detalle", "obras:evento_editar")),
        _AVISOS, _PERFIL,
    ],
}

INSIGNIAS = {
    "artista": ("🎨", "Artista"),
    "comprador": ("🖼️", "Coleccionista"),
    "curador": ("✅", "Curador"),
    "admin": ("⚙️", "Administrador"),
}


def navegacion(request):
    usuario = request.user
    if not usuario.is_authenticated:
        return {}
    clave = "admin" if usuario.es_admin else usuario.rol
    actual = request.resolver_match.view_name if request.resolver_match else ""
    items = [
        {"etiqueta": etiqueta, "icono": icono, "url": ruta, "activo": actual in activos}
        for etiqueta, icono, ruta, activos in MENUS.get(clave, [])
    ]
    emoji, nombre = INSIGNIAS.get(clave, ("", ""))
    return {"nav_items": items, "tema_rol": clave, "insignia_rol": (emoji, nombre)}
