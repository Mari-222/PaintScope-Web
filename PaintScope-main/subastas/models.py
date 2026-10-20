from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Subasta(models.Model):
    """Subasta en vivo de una obra dentro de un evento temático."""

    class Estado(models.TextChoices):
        PROGRAMADA = "programada", "Programada"
        ACTIVA = "activa", "Activa"
        CERRADA = "cerrada", "Cerrada"

    obra = models.ForeignKey("obras.Obra", on_delete=models.CASCADE, related_name="subastas")
    evento = models.ForeignKey("obras.Evento", on_delete=models.CASCADE, related_name="subastas")
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PROGRAMADA)
    precio_actual = models.DecimalField(max_digits=10, decimal_places=2)
    ganador = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="subastas_ganadas")
    pujas_suspendidas = models.BooleanField(default=False, help_text="Moderación: bloquea nuevas pujas")
    extensiones = models.PositiveSmallIntegerField(default=0)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha_fin"]

    def __str__(self):
        return f"Subasta de {self.obra.titulo} ({self.get_estado_display()})"

    @property
    def esta_activa(self):
        return self.estado == self.Estado.ACTIVA

    @property
    def cerrada(self):
        return self.estado == self.Estado.CERRADA

    @property
    def puja_ganadora(self):
        return self.pujas.order_by("-monto", "fecha_hora").first()

    @property
    def total_pujas(self):
        return self.pujas.count()

    @property
    def segundos_restantes(self):
        return max(0, int((self.fecha_fin - timezone.now()).total_seconds()))

    @property
    def monto_minimo(self):
        """La siguiente puja debe superar el precio actual (RF-09)."""
        return self.precio_actual + Decimal("1")


class Puja(models.Model):
    """Oferta económica de un comprador sobre una subasta (RF-09)."""

    subasta = models.ForeignKey(Subasta, on_delete=models.CASCADE, related_name="pujas")
    comprador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pujas")
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_hora = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-monto", "fecha_hora"]

    def __str__(self):
        return f"{self.comprador.email} ofrece {self.monto} por {self.subasta.obra.titulo}"
