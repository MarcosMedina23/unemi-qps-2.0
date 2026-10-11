"""
Admin de ``rutas``: rutas registradas e historial de consultas.
"""
from django.contrib import admin, messages

from .models import Conexion, Historial, Pasillo, Ruta
from .services import RutaNoEncontradaError, asegurar_camino


class ConexionEnLinea(admin.TabularInline):
    """Permite unir pasillos directamente desde la ficha de un pasillo."""

    model = Conexion
    fk_name = "pasillo_a"
    extra = 0
    autocomplete_fields = ("pasillo_b",)
    verbose_name = "conexión hacia"
    verbose_name_plural = "conexiones (caminos hacia otros pasillos)"


@admin.register(Pasillo)
class PasilloAdmin(admin.ModelAdmin):
    """
    Pasillos del campus (nodos del grafo de rutas). Cada zona se conecta
    sola a sus 2 pasillos más cercanos; aquí solo se unen pasillos entre sí.
    """

    list_display = ("codigo", "nombre", "latitud", "longitud", "total_conexiones")
    search_fields = ("codigo", "nombre")
    inlines = [ConexionEnLinea]

    @admin.display(description="conexiones")
    def total_conexiones(self, pasillo):
        return pasillo.conexiones_salientes.count() + pasillo.conexiones_entrantes.count()


@admin.register(Conexion)
class ConexionAdmin(admin.ModelAdmin):
    list_display = ("pasillo_a", "pasillo_b", "distancia_m")
    list_filter = ("pasillo_a", "pasillo_b")
    search_fields = ("pasillo_a__nombre", "pasillo_b__nombre")
    autocomplete_fields = ("pasillo_a", "pasillo_b")


@admin.register(Ruta)
class RutaAdmin(admin.ModelAdmin):
    """
    Si la distancia o el camino se dejan vacíos, se calculan al guardar
    (Dijkstra sobre el mapa de pasillos, ver rutas/services.py).
    """

    list_display = ("origen", "destino", "distancia", "tiempo_estimado", "puntos")
    list_filter = ("origen", "destino__tipo", "destino__zona")
    search_fields = ("origen__nombre", "destino__nombre")
    autocomplete_fields = ("origen", "destino")
    list_select_related = ("origen", "destino__zona")
    actions = ["recalcular_camino"]

    @admin.display(description="tiempo (min)")
    def tiempo_estimado(self, ruta):
        return ruta.tiempo_minutos

    @admin.display(description="waypoints")
    def puntos(self, ruta):
        return len(ruta.camino_json or [])

    def save_model(self, request, ruta, form, change):
        super().save_model(request, ruta, form, change)
        try:
            asegurar_camino(ruta)
        except RutaNoEncontradaError:
            self.message_user(
                request,
                "No se pudo calcular el camino automáticamente. Ingresa los waypoints a mano.",
                level=messages.WARNING,
            )

    @admin.action(description="Recalcular distancia y camino (Dijkstra)")
    def recalcular_camino(self, request, queryset):
        for ruta in queryset.select_related("origen", "destino"):
            asegurar_camino(ruta, forzar=True)
        self.message_user(request, f"{queryset.count()} ruta(s) recalculada(s).")


@admin.register(Historial)
class HistorialAdmin(admin.ModelAdmin):
    """Solo lectura: el historial se genera cuando los estudiantes usan la app."""

    list_display = ("usuario", "ruta", "fecha")
    list_filter = ("fecha", "ruta__destino__tipo", "ruta__origen")
    search_fields = ("usuario__username", "usuario__first_name", "ruta__destino__nombre")
    date_hierarchy = "fecha"
    list_select_related = ("usuario", "ruta__origen", "ruta__destino")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
