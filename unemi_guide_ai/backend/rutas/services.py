"""
Servicios de la app ``rutas``: cálculo del camino más corto.

El campus se modela como un grafo ponderado no dirigido:

    * Nodos:   pasillos (admin; si no hay, mapa_campus.py) + zonas (admin)
               + el destino elegido.
    * Aristas: conexiones entre pasillos (admin) + cada zona con sus 2
               pasillos más cercanos + el destino con su zona.
    * Peso:    distancia en metros.

El camino más corto se obtiene con el algoritmo de Dijkstra (cola de
prioridad ``heapq``, complejidad O((V + E) log V)) y se traduce a
indicaciones como «En Plaza Central, gira a la derecha y avanza 76 m».
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

from vision.utils import a_coordenadas, a_metros_locales
from zonas.models import Destino, Zona

from .mapa_campus import CONEXIONES_PASILLOS, PASILLOS, PASILLOS_POR_ZONA
from .models import Conexion, Pasillo

# Punto de referencia para pasar de lat/lng a metros (centro aproximado).
LAT_REFERENCIA = -2.149700
LNG_REFERENCIA = -79.603600

# Seno del ángulo por debajo del cual se considera "seguir recto" (~15°).
UMBRAL_GIRO = 0.26

CLAVE_DESTINO = "DESTINO"


class RutaNoEncontradaError(Exception):
    """No existe un camino entre el origen y el destino."""


@dataclass(frozen=True)
class Nodo:
    """Punto del grafo, en metros locales (X = este, Z = sur)."""

    clave: str
    nombre: str
    x: float
    z: float

    def distancia_a(self, otro: Nodo) -> float:
        return math.hypot(otro.x - self.x, otro.z - self.z)


class GrafoCampus:
    """Grafo ponderado no dirigido del campus."""

    def __init__(self):
        self._nodos: dict[str, Nodo] = {}
        self._vecinos: dict[str, dict[str, float]] = {}

    def agregar_nodo(self, nodo: Nodo) -> None:
        self._nodos[nodo.clave] = nodo
        self._vecinos.setdefault(nodo.clave, {})

    def conectar(self, clave_a: str, clave_b: str, distancia: float | None = None) -> None:
        """
        Une dos nodos. Si no se indica la distancia, se usa la línea recta
        entre ellos (la conexión del admin puede indicar un rodeo real).
        """
        if distancia is None:
            distancia = self._nodos[clave_a].distancia_a(self._nodos[clave_b])
        self._vecinos[clave_a][clave_b] = distancia
        self._vecinos[clave_b][clave_a] = distancia

    def nodo(self, clave: str) -> Nodo:
        return self._nodos[clave]

    def mas_cercanos(self, nodo: Nodo, candidatos: list[str], cantidad: int) -> list[str]:
        """Claves de los ``cantidad`` candidatos más cercanos a ``nodo``."""
        ordenados = sorted(candidatos, key=lambda clave: nodo.distancia_a(self._nodos[clave]))
        return ordenados[:cantidad]

    def camino_mas_corto(self, origen: str, destino: str) -> tuple[list[Nodo], float]:
        """
        Algoritmo de Dijkstra.

        Returns:
            (lista de nodos del camino, distancia total en metros)
        Raises:
            RutaNoEncontradaError: si el destino no es alcanzable.
        """
        distancias = {origen: 0.0}
        previo: dict[str, str] = {}
        visitados: set[str] = set()
        cola = [(0.0, origen)]

        while cola:
            distancia_actual, actual = heapq.heappop(cola)
            if actual in visitados:
                continue
            visitados.add(actual)
            if actual == destino:
                break
            for vecino, peso in self._vecinos[actual].items():
                nueva = distancia_actual + peso
                if nueva < distancias.get(vecino, math.inf):
                    distancias[vecino] = nueva
                    previo[vecino] = actual
                    heapq.heappush(cola, (nueva, vecino))

        if destino not in distancias:
            raise RutaNoEncontradaError(f"No hay camino entre {origen} y {destino}.")

        claves = [destino]
        while claves[-1] != origen:
            claves.append(previo[claves[-1]])
        return [self._nodos[clave] for clave in reversed(claves)], distancias[destino]


# ----------------------------------------------------------------------
# Indicaciones en lenguaje natural
# ----------------------------------------------------------------------
def _direccion_cardinal(desde: Nodo, hacia: Nodo) -> str:
    dx, dz = hacia.x - desde.x, hacia.z - desde.z
    if abs(dx) >= abs(dz):
        return "este" if dx > 0 else "oeste"
    return "sur" if dz > 0 else "norte"


def _giro(anterior: Nodo, actual: Nodo, siguiente: Nodo) -> str:
    """
    "derecha", "izquierda" o "recto" según el producto cruz de los tramos.
    Con X al este y Z al sur (como una pantalla vista desde arriba), un
    producto cruz positivo es un giro horario, es decir, a la derecha.
    """
    v1 = (actual.x - anterior.x, actual.z - anterior.z)
    v2 = (siguiente.x - actual.x, siguiente.z - actual.z)
    largo = math.hypot(*v1) * math.hypot(*v2)
    if largo == 0:
        return "recto"
    seno = (v1[0] * v2[1] - v1[1] * v2[0]) / largo
    if abs(seno) < UMBRAL_GIRO:
        return "recto"
    return "derecha" if seno > 0 else "izquierda"


def generar_instrucciones(camino: list[Nodo], destino: Destino) -> list[str]:
    """Una indicación por cada punto del camino."""
    origen = camino[0]
    if len(camino) == 1:
        return [f"Ya estás en {destino.nombre}."]

    indicaciones = [
        f"Desde {origen.nombre}, camina {origen.distancia_a(camino[1]):.0f} m "
        f"hacia el {_direccion_cardinal(origen, camino[1])}."
    ]
    for indice in range(1, len(camino) - 1):
        anterior, actual, siguiente = camino[indice - 1 : indice + 2]
        tramo = actual.distancia_a(siguiente)
        giro = _giro(anterior, actual, siguiente)
        if siguiente.clave == CLAVE_DESTINO:
            indicaciones.append(f"En {actual.nombre}, busca «{destino.nombre}» ({tramo:.0f} m).")
        elif giro == "recto":
            indicaciones.append(f"Al pasar por {actual.nombre}, continúa recto {tramo:.0f} m.")
        else:
            indicaciones.append(f"En {actual.nombre}, gira a la {giro} y avanza {tramo:.0f} m.")
    indicaciones.append(f"¡Llegaste a {destino.nombre}!")
    return indicaciones


# ----------------------------------------------------------------------
# API del módulo
# ----------------------------------------------------------------------
def _nodo_desde_coordenadas(clave, nombre, lat, lng) -> Nodo:
    x, z = a_metros_locales(lat, lng, LAT_REFERENCIA, LNG_REFERENCIA)
    return Nodo(clave, nombre, x, z)


def obtener_pasillos_y_conexiones():
    """
    Pasillos y conexiones del campus.

    Usa los registrados en el admin. Si todavía no hay ninguno, usa los
    valores por defecto de mapa_campus.py para que la app funcione igual.

    Returns:
        (pasillos, conexiones) con el formato:
            pasillos:   [(codigo, nombre, lat, lng), ...]
            conexiones: [(codigo_a, codigo_b, distancia_m o None), ...]
    """
    pasillos = [
        (p.codigo, p.nombre, p.latitud, p.longitud) for p in Pasillo.objects.all()
    ]
    if not pasillos:
        return list(PASILLOS), [(a, b, None) for a, b in CONEXIONES_PASILLOS]

    conexiones = [
        (c.pasillo_a.codigo, c.pasillo_b.codigo, c.distancia_m)
        for c in Conexion.objects.select_related("pasillo_a", "pasillo_b")
    ]
    return pasillos, conexiones


def construir_grafo(zonas, destino: Destino) -> GrafoCampus:
    """
    Arma el grafo: pasillos + zonas del admin + el destino elegido.
    Cada zona se conecta a sus pasillos más cercanos y el destino a su zona.
    """
    grafo = GrafoCampus()
    pasillos, conexiones = obtener_pasillos_y_conexiones()

    claves_pasillos = []
    for clave, nombre, lat, lng in pasillos:
        grafo.agregar_nodo(_nodo_desde_coordenadas(clave, nombre, lat, lng))
        claves_pasillos.append(clave)
    for clave_a, clave_b, distancia in conexiones:
        grafo.conectar(clave_a, clave_b, distancia)

    for zona in zonas:
        nodo_zona = _nodo_desde_coordenadas(f"Z{zona.pk}", zona.nombre, zona.latitud, zona.longitud)
        grafo.agregar_nodo(nodo_zona)
        for clave_pasillo in grafo.mas_cercanos(nodo_zona, claves_pasillos, PASILLOS_POR_ZONA):
            grafo.conectar(nodo_zona.clave, clave_pasillo)

    grafo.agregar_nodo(
        _nodo_desde_coordenadas(CLAVE_DESTINO, destino.nombre, destino.latitud, destino.longitud)
    )
    grafo.conectar(CLAVE_DESTINO, f"Z{destino.zona_id}")
    return grafo


def calcular_camino(origen: Zona, destino: Destino) -> tuple[list[dict], float]:
    """
    Camino más corto desde una zona hasta un destino.

    Returns:
        (waypoints, distancia_en_metros), donde cada waypoint es
        {"lat": ..., "lng": ..., "instruccion": "..."}.
    """
    grafo = construir_grafo(Zona.objects.all(), destino)
    camino, distancia = grafo.camino_mas_corto(f"Z{origen.pk}", CLAVE_DESTINO)
    indicaciones = generar_instrucciones(camino, destino)

    waypoints = []
    for nodo, instruccion in zip(camino, indicaciones, strict=True):
        lat, lng = a_coordenadas(nodo.x, nodo.z, LAT_REFERENCIA, LNG_REFERENCIA)
        waypoints.append({"lat": lat, "lng": lng, "instruccion": instruccion})
    return waypoints, round(distancia, 1)


def asegurar_camino(ruta, forzar=False):
    """
    Completa la distancia y el camino de una Ruta si están vacíos (o si
    ``forzar`` es True). Se usa al guardar en el admin y al consultar una
    ruta cargada desde seed_data.sql.
    """
    from vision.services import calcular_ruta_simulado  # Evita importación circular.

    if forzar or not ruta.camino_json or ruta.distancia is None:
        waypoints, distancia = calcular_ruta_simulado(ruta.origen, ruta.destino)
        if forzar or not ruta.camino_json:
            ruta.camino_json = waypoints
        if forzar or ruta.distancia is None:
            ruta.distancia = distancia
        if ruta.pk:
            ruta.save(update_fields=["camino_json", "distancia"])
    return ruta


def construir_escena(ruta) -> dict:
    """
    Datos de la escena 3D en metros, con la zona de origen como (0, 0).
    simulacion.js solo dibuja lo que esta función decide.
    """
    lat0, lng0 = ruta.origen.latitud, ruta.origen.longitud

    def a_xz(lat, lng):
        x, z = a_metros_locales(lat, lng, lat0, lng0)
        # "+ 0.0" convierte -0.0 en 0.0 (solo estético en el JSON).
        return round(x, 2) + 0.0, round(z, 2) + 0.0

    zonas = []
    for zona in Zona.objects.all():
        x, z = a_xz(zona.latitud, zona.longitud)
        zonas.append(
            {
                "nombre": zona.nombre,
                "x": x,
                "z": z,
                "es_origen": zona.pk == ruta.origen_id,
                "es_destino": zona.pk == ruta.destino.zona_id,
            }
        )

    camino = []
    for punto in ruta.camino_json:
        x, z = a_xz(punto["lat"], punto["lng"])
        camino.append({"x": x, "z": z, "instruccion": punto.get("instruccion", "")})

    return {"zonas": zonas, "camino": camino}
