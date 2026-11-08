"""
Reglas del motor de subastas.

Todo el flujo de negocio vive aquí para que las vistas queden delgadas y las
pruebas puedan ejercitar las reglas sin pasar por HTTP.
"""
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from notificaciones.servicio import notificar
from obras.models import Obra
from panel import parametros

from .models import Puja, Subasta


class PujaRechazada(Exception):
    """La puja no cumple una regla; el mensaje se muestra al comprador."""


# ---------------------------------------------------------------- creación
def crear_subasta(obra, evento):
    """Abre (o programa) la subasta de una obra aprobada dentro de un evento."""
    ahora = timezone.now()
    inicio = max(ahora, evento.fecha_inicio)
    fin = evento.fecha_fin
    if fin <= inicio:
        fin = inicio + timedelta(days=parametros.obtener("duracion_subasta_dias"))
    subasta = Subasta.objects.create(
        obra=obra,
        evento=evento,
        fecha_inicio=inicio,
        fecha_fin=fin,
        precio_actual=obra.precio_base,
        estado=Subasta.Estado.ACTIVA if inicio <= ahora else Subasta.Estado.PROGRAMADA,
    )
    obra.estado = Obra.Estado.EN_SUBASTA
    obra.save(update_fields=["estado", "actualizada"])
    return subasta


# ---------------------------------------------------------------- estados
def sincronizar_estados():
    """
    Abre las subastas cuya hora llegó y cierra las vencidas.
    Se llama en cada vista del motor y también con `manage.py cerrar_subastas`.
    """
    ahora = timezone.now()
    Subasta.objects.filter(
        estado=Subasta.Estado.PROGRAMADA, fecha_inicio__lte=ahora, fecha_fin__gt=ahora
    ).update(estado=Subasta.Estado.ACTIVA)
    vencidas = Subasta.objects.filter(
        estado__in=[Subasta.Estado.PROGRAMADA, Subasta.Estado.ACTIVA], fecha_fin__lte=ahora
    ).values_list("pk", flat=True)
    for pk in list(vencidas):
        cerrar_subasta(pk)


def cerrar_subasta(pk):
    """Cierra una subasta, define el ganador y avisa a los involucrados."""
    with transaction.atomic():
        subasta = Subasta.objects.select_for_update().select_related("obra__artista").get(pk=pk)
        if subasta.estado == Subasta.Estado.CERRADA:
            return subasta
        mejor = subasta.puja_ganadora
        subasta.estado = Subasta.Estado.CERRADA
        subasta.ganador = mejor.comprador if mejor else None
        subasta.save(update_fields=["estado", "ganador"])

        obra, artista = subasta.obra, subasta.obra.artista
        url = reverse("subastas:detalle", args=[subasta.pk])
        if mejor:
            obra.estado = Obra.Estado.VENDIDA
            notificar(mejor.comprador, "subasta_ganada", "¡Ganaste la subasta!",
                      f"Tu puja de ${mejor.monto:,.0f} por «{obra.titulo}» fue la más alta.", url)
            notificar(artista, "subasta_cerrada", "Tu obra se vendió",
                      f"«{obra.titulo}» cerró en ${mejor.monto:,.0f}.", url)
        else:
            obra.estado = Obra.Estado.APROBADA  # sin pujas: queda disponible para otro evento
            notificar(artista, "subasta_cerrada", "Subasta cerrada sin pujas",
                      f"«{obra.titulo}» no recibió pujas y volvió a tu lista de obras aprobadas.", url)
        obra.save(update_fields=["estado", "actualizada"])

        # Los demás compradores que pujaron también reciben el aviso de cierre
        otros = (subasta.pujas.exclude(comprador=subasta.ganador)
                 .values_list("comprador", flat=True).distinct())
        from usuarios.models import Usuario
        for comprador in Usuario.objects.filter(pk__in=list(otros)):
            notificar(comprador, "subasta_cerrada", "Una subasta en la que pujaste cerró",
                      f"«{obra.titulo}» ya tiene ganador.", url)

    evaluar_insignia(artista)
    return subasta


def ventas_exitosas(artista):
    return Subasta.objects.filter(obra__artista=artista, ganador__isnull=False).count()


def evaluar_insignia(artista):
    """RF-13: otorga el sello de Verificado al alcanzar el umbral de ventas."""
    if artista.insignia_verificado:
        return False
    if ventas_exitosas(artista) >= parametros.obtener("ventas_para_verificado"):
        artista.insignia_verificado = True
        artista.save(update_fields=["insignia_verificado"])
        notificar(artista, "sistema", "Ya eres artista verificado",
                  "Alcanzaste el volumen de ventas necesario y tu perfil ahora lleva el sello de Verificado.",
                  reverse("obras:perfil_artista", args=[artista.pk]))
        return True
    return False


# ------------------------------------------------------------------- pujas
def registrar_puja(subasta_id, usuario, monto):
    """
    Registra una puja validando todas las reglas (RF-09, RF-10, RF-16).
    Lanza PujaRechazada con un mensaje claro si algo no se cumple.
    """
    try:
        monto = Decimal(str(monto).replace(",", "."))
    except Exception:
        raise PujaRechazada("Ingresa un monto numérico.")

    with transaction.atomic():
        # Bloquea la fila: dos pujas simultáneas no pueden pisarse
        subasta = Subasta.objects.select_for_update().select_related("obra__artista").get(pk=subasta_id)
        ahora = timezone.now()

        if subasta.estado == Subasta.Estado.ACTIVA and subasta.fecha_fin <= ahora:
            raise PujaRechazada("La subasta ya terminó.")
        if subasta.estado != Subasta.Estado.ACTIVA:
            raise PujaRechazada("Esta subasta no está abierta para pujas.")
        if subasta.pujas_suspendidas:
            raise PujaRechazada("Las pujas de esta obra están suspendidas por moderación.")
        if not usuario.puede_pujar:
            raise PujaRechazada("Tu rol no puede pujar en subastas.")
        if subasta.obra.artista_id == usuario.pk:
            raise PujaRechazada("No puedes pujar por tu propia obra.")
        if not usuario.tiene_metodo_pago:
            raise PujaRechazada("Registra un método de pago en tu perfil para poder pujar.")
        if monto <= subasta.precio_actual:
            raise PujaRechazada(
                f"Tu puja debe ser mayor a la puja actual (${subasta.precio_actual:,.0f}). Ingresa un monto mayor."
            )

        anterior = subasta.puja_ganadora
        puja = Puja.objects.create(subasta=subasta, comprador=usuario, monto=monto, fecha_hora=ahora)
        subasta.precio_actual = monto

        # RF-10: puja de último momento → se extiende el cierre
        ventana = timedelta(minutes=parametros.obtener("ventana_extension_minutos"))
        extendida = subasta.fecha_fin - ahora <= ventana
        if extendida:
            subasta.fecha_fin += timedelta(hours=parametros.obtener("horas_extension"))
            subasta.extensiones += 1
        subasta.save(update_fields=["precio_actual", "fecha_fin", "extensiones"])

        # RF-14: avisar al comprador desplazado
        if anterior and anterior.comprador_id != usuario.pk:
            notificar(anterior.comprador, "puja_superada", "Superaron tu puja",
                      f"Alguien ofreció ${monto:,.0f} por «{subasta.obra.titulo}».",
                      reverse("subastas:detalle", args=[subasta.pk]))

        # RF-14: confirmar la puja a quien la hizo
        mensaje = f"Tu puja de ${monto:,.0f} por «{subasta.obra.titulo}» quedó registrada."
        if extendida:
            mensaje += " Entró al final, así que el cierre se extendió."
        notificar(usuario, "puja_confirmada", "Puja confirmada", mensaje,
                  reverse("subastas:detalle", args=[subasta.pk]))

    puja.extendida = extendida
    return puja


# ------------------------------------------------------------ consultas
def estado_para_json(subasta):
    """Datos mínimos que el navegador consulta cada pocos segundos."""
    return {
        "id": subasta.pk,
        "precio": float(subasta.precio_actual),
        "pujas": subasta.pujas.count(),
        "fin": subasta.fecha_fin.isoformat(),
        "segundos": subasta.segundos_restantes,
        "estado": subasta.estado,
        "extensiones": subasta.extensiones,
        "suspendida": subasta.pujas_suspendidas,
    }