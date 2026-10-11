"""
Admin de ``zonas``: zonas del campus y sus destinos.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import Destino, Zona


class ConImagenFilter(admin.SimpleListFilter):
    """Filtro lateral: zonas con o sin imagen de referencia."""

    title = "imagen de referencia"
    parameter_name = "con_imagen"

    def lookups(self, request, model_admin):
        return (("si", "Con imagen"), ("no", "Sin imagen"))

    def queryset(self, request, queryset):
        if self.value() == "si":
            return queryset.exclude(imagen_referencia="")
        if self.value() == "no":
            return queryset.filter(imagen_referencia="")
        return queryset


class DestinoEnLinea(admin.TabularInline):
    """Permite agregar destinos directamente desde la ficha de la zona."""

    model = Destino
    extra = 0
    fields = ("nombre", "tipo", "latitud", "longitud")


@admin.register(Zona)
class ZonaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion", "latitud", "longitud", "total_destinos")
    list_filter = (ConImagenFilter,)
    search_fields = ("nombre", "descripcion")
    readonly_fields = ("vista_previa",)
    fields = ("nombre", "descripcion", ("latitud", "longitud"), "imagen_referencia", "vista_previa")
    inlines = [DestinoEnLinea]

    @admin.display(description="destinos")
    def total_destinos(self, zona):
        return zona.destinos.count()

    @admin.display(description="vista previa")
    def vista_previa(self, zona):
        if not zona.imagen_referencia:
            return "Sin imagen"
        return format_html(
            '<img src="{}" alt="{}" width="240">', zona.imagen_referencia.url, zona.nombre
        )


@admin.register(Destino)
class DestinoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "zona", "tipo")
    list_filter = ("tipo", "zona")
    search_fields = ("nombre", "zona__nombre")
    autocomplete_fields = ("zona",)
    list_select_related = ("zona",)
