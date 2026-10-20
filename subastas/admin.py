from django.contrib import admin

from .models import Puja, Subasta


class PujaInline(admin.TabularInline):
    model = Puja
    extra = 0
    readonly_fields = ("comprador", "monto", "fecha_hora")


@admin.register(Subasta)
class SubastaAdmin(admin.ModelAdmin):
    list_display = ("obra", "evento", "estado", "precio_actual", "fecha_fin", "ganador")
    list_filter = ("estado", "evento")
    inlines = [PujaInline]
