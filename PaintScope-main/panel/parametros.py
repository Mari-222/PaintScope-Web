"""
Parámetros globales de la plataforma (RF-15, PAIN-29).

Se guardan en la tabla ParametroGlobal; si una clave aún no existe en la base
se usa el valor por defecto definido aquí, así no hace falta sembrar datos.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Definicion:
    clave: str
    etiqueta: str
    ayuda: str
    tipo: str  # "int" | "bool"
    defecto: object


DEFINICIONES = [
    Definicion("ventana_extension_minutos", "Ventana de extensión (minutos)",
               "Una puja dentro de los últimos N minutos extiende el cierre de la subasta (RF-10).", "int", 5),
    Definicion("horas_extension", "Horas que se extiende una subasta",
               "Tiempo que se suma al cierre cuando entra una puja de último momento.", "int", 6),
    Definicion("duracion_subasta_dias", "Duración predeterminada (días)",
               "Se usa si el evento termina antes de que la subasta pueda abrir.", "int", 7),
    Definicion("ventas_para_verificado", "Ventas para la insignia de verificado",
               "Subastas ganadas que un artista debe acumular para recibir la insignia (RF-13).", "int", 3),
    Definicion("visitas_hora_inicio", "Primera hora de visitas",
               "Hora del día (0-23) en que empieza la agenda de visitas guiadas.", "int", 10),
    Definicion("visitas_hora_fin", "Última hora de visitas",
               "Hora del día (1-24) en que termina la agenda de visitas guiadas.", "int", 16),
    Definicion("visitas_dias_adelante", "Días de agenda disponibles",
               "Cuántos días hacia adelante se ofrecen horarios de visita.", "int", 7),
    Definicion("modo_mantenimiento", "Modo mantenimiento",
               "Solo los administradores pueden entrar mientras esté activo.", "bool", False),
]

_POR_CLAVE = {d.clave: d for d in DEFINICIONES}


def _convertir(definicion, texto):
    if definicion.tipo == "bool":
        return str(texto).lower() in ("1", "true", "si", "sí", "on")
    return int(texto)


def obtener(clave):
    """Devuelve el valor vigente del parámetro (ya convertido a int o bool)."""
    from .models import ParametroGlobal

    definicion = _POR_CLAVE[clave]
    fila = ParametroGlobal.objects.filter(clave=clave).first()
    if fila is None:
        return definicion.defecto
    try:
        return _convertir(definicion, fila.valor)
    except (TypeError, ValueError):
        return definicion.defecto


def guardar(clave, valor):
    from .models import ParametroGlobal

    definicion = _POR_CLAVE[clave]
    if definicion.tipo == "bool":
        valor = "true" if valor else "false"
    ParametroGlobal.objects.update_or_create(clave=clave, defaults={"valor": str(valor)})


def todos():
    """Lista de (definicion, valor_actual) para el panel de administración."""
    return [(d, obtener(d.clave)) for d in DEFINICIONES]
