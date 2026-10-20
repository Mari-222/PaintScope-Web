from django.conf import settings
from django.db import models
from django.utils import timezone


class Evento(models.Model):
    """Evento temático por temporada o categoría (RF-07)."""

    nombre = models.CharField(max_length=120)
    tematica = models.CharField("temática", max_length=120)
    temporada = models.CharField(max_length=60, help_text="Ej. Semana Santa, Black Friday, Todo el año")
    fecha_inicio = models.DateTimeField("inicio de las subastas")
    fecha_fin = models.DateTimeField("fin de las subastas")
    cierre_convocatoria = models.DateTimeField(
        "cierre de la convocatoria", help_text="Hasta cuándo los artistas pueden postular obras"
    )
    publicado = models.BooleanField(default=False)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                                   related_name="eventos_creados")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return self.nombre

    @property
    def convocatoria_abierta(self):
        return self.publicado and timezone.now() <= self.cierre_convocatoria


class Obra(models.Model):
    """Obra del portafolio de un artista (RF-04)."""

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        PENDIENTE = "pendiente", "Pendiente de revisión"
        APROBADA = "aprobada", "Aprobada"
        EN_SUBASTA = "en_subasta", "En subasta"
        VENDIDA = "vendida", "Vendida"

    TECNICAS = [
        ("Óleo sobre lienzo", "Óleo sobre lienzo"),
        ("Óleo sobre tabla", "Óleo sobre tabla"),
        ("Acuarela sobre papel", "Acuarela sobre papel"),
        ("Acrílico sobre lienzo", "Acrílico sobre lienzo"),
        ("Técnica mixta", "Técnica mixta"),
        ("Otra", "Otra"),
    ]
    CATEGORIAS = [
        ("Paisaje", "Paisaje"),
        ("Retrato", "Retrato"),
        ("Abstracto", "Abstracto"),
        ("Naturaleza muerta", "Naturaleza muerta"),
        ("Otro", "Otro"),
    ]

    artista = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="obras")
    titulo = models.CharField("título", max_length=150)
    descripcion = models.TextField("descripción")
    tecnica = models.CharField("técnica", max_length=60, choices=TECNICAS)
    categoria = models.CharField("categoría", max_length=30, choices=CATEGORIAS, default="Paisaje")
    dimensiones = models.CharField(max_length=60, help_text="Ej. 80 × 110 cm")
    anio = models.PositiveSmallIntegerField("año", null=True, blank=True)
    imagen = models.ImageField(upload_to="obras/", blank=True)
    # Solo para los datos de demostración, que usan fotos del prototipo
    imagen_url = models.URLField(blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.BORRADOR)
    precio_base = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    curador = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="obras_evaluadas")
    motivo_rechazo = models.CharField(max_length=300, blank=True)
    restringida = models.BooleanField(default=False, help_text="Oculta la obra del catálogo (moderación)")
    creada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creada"]

    def __str__(self):
        return f"{self.titulo} — {self.artista.nombre_visible}"

    @property
    def imagen_src(self):
        if self.imagen:
            return self.imagen.url
        return self.imagen_url

    @property
    def editable(self):
        return self.estado == self.Estado.BORRADOR


class Postulacion(models.Model):
    """Una obra postulada a un evento, pendiente de evaluación del curador (RF-05)."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de revisión"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="postulaciones")
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="postulaciones")
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    curador = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="evaluaciones")
    motivo = models.CharField(max_length=300, blank=True)
    creada = models.DateTimeField(auto_now_add=True)
    resuelta = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creada"]

    def __str__(self):
        return f"{self.obra.titulo} → {self.evento.nombre} ({self.get_estado_display()})"
