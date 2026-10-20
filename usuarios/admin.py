from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import MetodoPago, Usuario


class UsuarioCreacionForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ("email", "first_name", "rol")


class UsuarioCambioForm(UserChangeForm):
    class Meta:
        model = Usuario
        fields = "__all__"


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    # El modelo no tiene `username` (se entra con correo), así que los
    # fieldsets y formularios de UserAdmin se redefinen sin ese campo.
    form = UsuarioCambioForm
    add_form = UsuarioCreacionForm
    ordering = ("email",)
    list_display = ("email", "first_name", "rol", "insignia_verificado", "is_active", "is_staff")
    list_filter = ("rol", "is_staff", "is_active")
    search_fields = ("email", "first_name", "last_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Datos personales", {"fields": ("first_name", "last_name", "telefono")}),
        ("Rol en PaintScope", {"fields": ("rol", "insignia_verificado")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "rol", "password1", "password2"),
        }),
    )


@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "tipo", "ultimos4", "vencimiento")
