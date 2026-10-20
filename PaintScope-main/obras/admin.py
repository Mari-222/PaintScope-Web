from django.contrib import admin

from .models import Evento, Obra, Postulacion


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "temporada", "fecha_inicio", "fecha_fin", "publicado")
    list_filter = ("publicado", "temporada")


@admin.register(Obra)
class ObraAdmin(admin.ModelAdmin):
    list_display = ("titulo", "artista", "estado", "precio_base", "restringida")
    list_filter = ("estado", "restringida", "tecnica")
    search_fields = ("titulo", "artista__email", "artista__first_name")


@admin.register(Postulacion)
class PostulacionAdmin(admin.ModelAdmin):
    list_display = ("obra", "evento", "estado", "curador", "creada")
    list_filter = ("estado",)
