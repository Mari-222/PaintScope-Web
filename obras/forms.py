from django import forms
from django.utils import timezone

from .models import Evento, Obra

MAX_IMAGEN = 10 * 1024 * 1024  # 10 MB, como indica el prototipo


class ObraForm(forms.ModelForm):
    class Meta:
        model = Obra
        fields = ("titulo", "descripcion", "tecnica", "categoria", "dimensiones", "anio", "imagen")
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 4}),
                   "dimensiones": forms.TextInput(attrs={"placeholder": "80 × 110 cm"}),
                   "titulo": forms.TextInput(attrs={"placeholder": "Ej. Luz sobre el estuario"})}

    def clean_imagen(self):
        imagen = self.cleaned_data.get("imagen")
        if imagen and hasattr(imagen, "size") and imagen.size > MAX_IMAGEN:
            raise forms.ValidationError("La imagen supera los 10 MB.")
        return imagen

    def clean(self):
        datos = super().clean()
        # RF-04: la obra necesita al menos una imagen
        if not datos.get("imagen") and not (self.instance and self.instance.imagen_src):
            self.add_error("imagen", "Sube una imagen de la obra.")
        return datos


class PostulacionForm(forms.Form):
    evento = forms.ModelChoiceField(queryset=Evento.objects.none(), label="Evento temático",
                                    empty_label="Elige un evento")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["evento"].queryset = Evento.objects.filter(publicado=True).order_by("cierre_convocatoria")

    def clean_evento(self):
        evento = self.cleaned_data["evento"]
        if not evento.convocatoria_abierta:
            raise forms.ValidationError("La convocatoria de este evento ya cerró. Elige otro evento.")
        return evento


class EvaluacionForm(forms.Form):
    decision = forms.ChoiceField(choices=[("aprobar", "Aprobar"), ("rechazar", "Rechazar")])
    precio_base = forms.DecimalField(label="Precio base de salida (USD)", required=False,
                                     min_value=1, max_digits=10, decimal_places=2)
    motivo = forms.CharField(label="Motivo del rechazo", required=False, max_length=300,
                             widget=forms.Textarea(attrs={"rows": 3}))

    def clean(self):
        datos = super().clean()
        if datos.get("decision") == "aprobar" and not datos.get("precio_base"):
            self.add_error("precio_base", "Define el precio base de salida para aprobar la obra.")
        if datos.get("decision") == "rechazar" and not (datos.get("motivo") or "").strip():
            self.add_error("motivo", "Indica el motivo del rechazo.")
        return datos


class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = ("nombre", "tematica", "temporada", "fecha_inicio", "fecha_fin", "cierre_convocatoria")
        widgets = {
            "fecha_inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "fecha_fin": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "cierre_convocatoria": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in ("fecha_inicio", "fecha_fin", "cierre_convocatoria"):
            self.fields[campo].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"]

    def clean(self):
        datos = super().clean()
        inicio, fin, cierre = (datos.get(k) for k in ("fecha_inicio", "fecha_fin", "cierre_convocatoria"))
        if inicio and fin and fin <= inicio:
            self.add_error("fecha_fin", "El fin debe ser posterior al inicio.")
        if cierre and fin and cierre > fin:
            self.add_error("cierre_convocatoria", "La convocatoria debe cerrar antes de que terminen las subastas.")
        return datos
