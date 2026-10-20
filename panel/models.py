from django.db import models


class ParametroGlobal(models.Model):
    """Pareja clave/valor editable desde el panel de administración."""

    clave = models.CharField(max_length=60, unique=True)
    valor = models.CharField(max_length=120)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "parámetro global"
        verbose_name_plural = "parámetros globales"

    def __str__(self):
        return f"{self.clave} = {self.valor}"
