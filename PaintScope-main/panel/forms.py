from django import forms
from django.contrib.auth.password_validation import validate_password

from usuarios.models import Usuario

from . import parametros


class UsuarioPanelForm(forms.ModelForm):
    """Crear o editar un usuario desde el panel (CU-08)."""

    password = forms.CharField(label="Contraseña", required=False, widget=forms.PasswordInput,
                               help_text="Déjala vacía para no cambiarla al editar.")

    class Meta:
        model = Usuario
        fields = ("first_name", "email", "telefono", "rol")
        labels = {"first_name": "Nombre", "email": "Correo electrónico", "telefono": "Teléfono", "rol": "Rol"}

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        otros = Usuario.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if otros.exists():
            raise forms.ValidationError("Ese correo ya pertenece a otra cuenta.")
        return email

    def clean(self):
        datos = super().clean()
        if not self.instance.pk and not datos.get("password"):
            self.add_error("password", "Define una contraseña para la cuenta nueva.")
        if datos.get("password"):
            try:
                validate_password(datos["password"], self.instance)
            except forms.ValidationError as error:
                self.add_error("password", error)
        return datos

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get("password"):
            usuario.set_password(self.cleaned_data["password"])
        usuario.is_staff = usuario.rol == Usuario.Rol.ADMIN or usuario.is_superuser
        if commit:
            usuario.save()
        return usuario


class ParametrosForm(forms.Form):
    """Un campo por parámetro definido en panel.parametros."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for definicion, valor in parametros.todos():
            if definicion.tipo == "bool":
                campo = forms.BooleanField(required=False, initial=valor)
            else:
                campo = forms.IntegerField(min_value=0, initial=valor)
            campo.label = definicion.etiqueta
            campo.help_text = definicion.ayuda
            self.fields[definicion.clave] = campo

    def clean(self):
        datos = super().clean()
        inicio, fin = datos.get("visitas_hora_inicio"), datos.get("visitas_hora_fin")
        if inicio is not None and fin is not None:
            if inicio > 23:
                self.add_error("visitas_hora_inicio", "Usa una hora entre 0 y 23.")
            if fin > 24 or fin <= inicio:
                self.add_error("visitas_hora_fin", "Debe ser mayor que la primera hora y no pasar de 24.")
        if datos.get("horas_extension") == 0:
            self.add_error("horas_extension", "Debe ser al menos 1 hora.")
        return datos

    def guardar(self):
        for clave, valor in self.cleaned_data.items():
            parametros.guardar(clave, valor)
