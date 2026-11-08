from django.conf import settings
from django.db import models


class Notificacion(models.Model):
    """Aviso dentro de la aplicación (RF-14: no se envía por correo ni SMS)."""

    class Tipo(models.TextChoices):
        PUJA_SUPERADA = "puja_superada", "Puja superada"
        PUJA_CONFIRMADA = "puja_confirmada", "Puja confirmada"
        SUBASTA_CERRADA = "subasta_cerrada", "Subasta cerrada"
        SUBASTA_GANADA = "subasta_ganada", "Subasta ganada"
        OBRA_APROBADA = "obra_aprobada", "Obra aprobada"
        OBRA_RECHAZADA = "obra_rechazada", "Obra rechazada"
        VISITA = "visita", "Visita confirmada"
        POSTULACION = "postulacion", "Nueva postulación"
        SISTEMA = "sistema", "Aviso del sistema"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="notificaciones")
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.SISTEMA)
    titulo = models.CharField(max_length=120)
    mensaje = models.CharField(max_length=300)
    url = models.CharField(max_length=200, blank=True)
    leida = models.BooleanField(default=False)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creada", "-id"]
        verbose_name = "notificación"
        verbose_name_plural = "notificaciones"

    def __str__(self):
        return f"{self.usuario_id}: {self.titulo}"