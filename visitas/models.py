from django.conf import settings
from django.db import models


class Visita(models.Model):
    """Visita guiada presencial o virtual para apreciar una obra (RF-12)."""

    class Tipo(models.TextChoices):
        PRESENCIAL = "presencial", "Presencial"
        VIRTUAL = "virtual", "Virtual"

    class Estado(models.TextChoices):
        AGENDADA = "agendada", "Agendada"
        CANCELADA = "cancelada", "Cancelada"

    obra = models.ForeignKey("obras.Obra", on_delete=models.CASCADE, related_name="visitas")
    comprador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="visitas")
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    fecha_hora = models.DateTimeField()
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.AGENDADA)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha_hora"]

    def __str__(self):
        return f"{self.get_tipo_display()} · {self.obra.titulo} · {self.fecha_hora:%d/%m %H:%M}"
