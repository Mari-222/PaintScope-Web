import re
from datetime import date

from django import forms
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm

from .models import MetodoPago, Usuario


class RegistroForm(UserCreationForm):
    # RF-01: solo Artista o Comprador pueden auto-registrarse
    rol = forms.ChoiceField(
        label="Tipo de cuenta",
        choices=[
            (Usuario.Rol.ARTISTA, "Artista"),
            (Usuario.Rol.COMPRADOR, "Comprador/Coleccionista"),
        ],
    )

    class Meta:
        model = Usuario
        fields = ("first_name", "email", "rol")
        labels = {"first_name": "Nombre", "email": "Correo electrónico"}

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este correo ya está registrado. Usa otro o inicia sesión.")
        return email

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.rol = self.cleaned_data["rol"]
        if commit:
            usuario.save()
        return usuario


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ("first_name", "email", "telefono")
        labels = {"first_name": "Nombre", "email": "Correo electrónico", "telefono": "Teléfono"}

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ese correo ya pertenece a otra cuenta.")
        return email


class CambioPasswordForm(PasswordChangeForm):
    """PasswordChangeForm de Django con etiquetas del sistema."""


def _luhn_valido(numero):
    suma, alterna = 0, False
    for digito in reversed(numero):
        d = int(digito)
        if alterna:
            d *= 2
            if d > 9:
                d -= 9
        suma += d
        alterna = not alterna
    return suma % 10 == 0


class MetodoPagoForm(forms.Form):
    tipo = forms.ChoiceField(label="Tipo de tarjeta", choices=MetodoPago.Tipo.choices)
    titular = forms.CharField(label="Nombre del titular", max_length=80)
    numero = forms.CharField(label="Número de tarjeta", max_length=23,
                             widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}))
    vencimiento = forms.CharField(label="Vence (MM/AA)", max_length=5,
                                  widget=forms.TextInput(attrs={"placeholder": "08/28"}))

    def clean_numero(self):
        numero = re.sub(r"[\s-]", "", self.cleaned_data["numero"])
        if not numero.isdigit() or not 13 <= len(numero) <= 19 or not _luhn_valido(numero):
            raise forms.ValidationError("El número de tarjeta no es válido.")
        return numero

    def clean_vencimiento(self):
        valor = self.cleaned_data["vencimiento"].strip()
        coincide = re.fullmatch(r"(0[1-9]|1[0-2])/(\d{2})", valor)
        if not coincide:
            raise forms.ValidationError("Usa el formato MM/AA, por ejemplo 08/28.")
        mes, anio = int(coincide.group(1)), 2000 + int(coincide.group(2))
        hoy = date.today()
        if (anio, mes) < (hoy.year, hoy.month):
            raise forms.ValidationError("La tarjeta está vencida.")
        return valor

    def guardar(self, usuario):
        """Guarda solo los últimos 4 dígitos; el número completo se descarta."""
        return MetodoPago.objects.create(
            usuario=usuario,
            tipo=self.cleaned_data["tipo"],
            titular=self.cleaned_data["titular"],
            ultimos4=self.cleaned_data["numero"][-4:],
            vencimiento=self.cleaned_data["vencimiento"],
        )
