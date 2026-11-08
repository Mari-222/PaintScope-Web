from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _crear(self, email, password, **extra):
        if not email:
            raise ValueError("El correo es obligatorio")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._crear(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("rol", "admin")
        return self._crear(email, password, **extra)


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        ARTISTA = "artista", "Artista"
        CURADOR = "curador", "Curador/Moderador"
        COMPRADOR = "comprador", "Comprador/Coleccionista"
        ADMIN = "admin", "Administrador"

    username = None                       # el login es por correo (RF-02)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.COMPRADOR)
    # RF-13: sello que el sistema otorga solo al artista con ventas exitosas
    insignia_verificado = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name"]
    objects = UsuarioManager()

    def __str__(self):
        return f"{self.email} ({self.get_rol_display()})"

    @property
    def nombre_visible(self):
        return self.first_name or self.email.split("@")[0]

    @property
    def es_admin(self):
        return self.rol == self.Rol.ADMIN or self.is_superuser

    @property
    def es_curador(self):
        return self.rol == self.Rol.CURADOR

    @property
    def es_artista(self):
        return self.rol == self.Rol.ARTISTA

    @property
    def es_comprador(self):
        return self.rol == self.Rol.COMPRADOR

    @property
    def puede_pujar(self):
        """add qeu compradores y art puedan pujar"""
        return self.rol in (self.Rol.COMPRADOR, self.Rol.ARTISTA)

    @property
    def tiene_metodo_pago(self):
        """RF-16: sin método de pago registrado no se puede pujar."""
        return self.metodos_pago.exists()


class MetodoPago(models.Model):
    """
    Método de pago del comprador (RF-16).

    Por seguridad solo se guardan los últimos 4 dígitos; el número completo
    nunca se almacena. No hay cobros reales (el pago/envío quedó fuera del alcance).
    """

    class Tipo(models.TextChoices):
        CREDITO = "credito", "Tarjeta de crédito"
        DEBITO = "debito", "Tarjeta de débito"

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="metodos_pago")
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.CREDITO)
    titular = models.CharField(max_length=80)
    ultimos4 = models.CharField(max_length=4)
    vencimiento = models.CharField(max_length=5, help_text="MM/AA")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]
        verbose_name = "método de pago"
        verbose_name_plural = "métodos de pago"

    def __str__(self):
        return f"{self.get_tipo_display()} terminada en {self.ultimos4}"