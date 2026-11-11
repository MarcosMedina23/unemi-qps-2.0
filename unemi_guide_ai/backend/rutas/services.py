"""
Servicios de la app ``rutas``: cálculo del camino más corto.

IDEA GENERAL (para explicarlo en la exposición):

    El campus es un GRAFO:
        * Nodos (puntos):  los pasillos, las zonas y el destino elegido.
        * Aristas (líneas): qué punto se conecta con cuál.
        * Peso:            la distancia en metros de cada línea.

    Con el algoritmo de DIJKSTRA (ya viene hecho en la librería NetworkX)
    buscamos el camino de menor distancia total. Luego convertimos ese
    camino en indicaciones: «En Plaza Central, gira a la derecha y avanza 76 m».

Cada punto del grafo es un diccionario sencillo:
    {"clave": "P-01", "nombre": "Plaza Central", "x": 12.5, "z": -30.0}
donde x y z son metros (X = hacia el este, Z = hacia el sur).
"""
import math

import networkx as nx

from vision.utils import a_coordenadas, a_metros_locales
from zonas.models import Zona

from .mapa_campus import CONEXIONES_PASILLOS, PASILLOS, PASILLOS_POR_ZONA
from .models import Conexion, Pasillo

# Punto del campus que usamos como (0, 0) para pasar de lat/lng a metros.
# Es el MISMO (0, 0) del modelo 3D de Unity y de campus_unemi.json, así la
# escena que se envía a Unity y a la web cae en el lugar correcto del campus.
LAT_REFERENCIA = -2.149700
LNG_REFERENCIA = -79.603600

# Si el giro es menor a unos 15 grados, lo tomamos como "seguir recto".
UMBRAL_GIRO = 0.26

# Código de los pasillos que crea "manage.py cargar_campus" (las calles).
PREFIJO_CALLE = "C-"

# Tramos más cortos que esto (metros) no generan una indicación propia.
TRAMO_MINIMO = 8

# Clave fija del nodo destino dentro del grafo.
CLAVE_DESTINO = "DESTINO"


class RutaNoEncontradaError(Exception):
    """Se lanza cuando no existe ningún camino entre el origen y el destino."""


# ----------------------------------------------------------------------
# 1. Funciones básicas del grafo
# ----------------------------------------------------------------------
def crear_punto(clave, nombre, lat, lng):
    """Crea un punto del grafo convirtiendo latitud/longitud a metros."""
    x, z = a_metros_locales(lat, lng, LAT_REFERENCIA, LNG_REFERENCIA)
    return {"clave": clave, "nombre": nombre, "x": x, "z": z}


def distancia_entre(punto_a, punto_b):
    """Distancia en línea recta (teorema de Pitágoras) entre dos puntos."""
    return math.hypot(punto_b["x"] - punto_a["x"], punto_b["z"] - punto_a["z"])


def agregar_punto(grafo, punto):
    """Agrega un punto al grafo. Guardamos el diccionario dentro del nodo."""
    grafo.add_node(punto["clave"], punto=punto)


def obtener_punto(grafo, clave):
    """Devuelve el diccionario del punto guardado con esa clave."""
    return grafo.nodes[clave]["punto"]


def conectar(grafo, clave_a, clave_b, distancia=None):
    """
    Une dos puntos con una línea.

    Si no nos dan la distancia, usamos la línea recta entre ellos.
    (En el admin se puede escribir una distancia mayor si hay un rodeo real.)
    """
    if distancia is None:
        distancia = distancia_entre(obtener_punto(grafo, clave_a), obtener_punto(grafo, clave_b))
    grafo.add_edge(clave_a, clave_b, weight=distancia)


def camino_mas_corto(grafo, clave_origen, clave_destino):
    """
    Algoritmo de Dijkstra (lo hace NetworkX por nosotros).

    Returns:
        (lista de puntos del camino, distancia total en metros)
    Raises:
        RutaNoEncontradaError: si no hay forma de llegar.
    """
    try:
        distancia, claves = nx.single_source_dijkstra(
            grafo, clave_origen, clave_destino, weight="weight"
        )
    except (nx.NetworkXNoPath, nx.NodeNotFound) as error:
        mensaje = f"No hay camino entre {clave_origen} y {clave_destino}."
        raise RutaNoEncontradaError(mensaje) from error

    puntos = [obtener_punto(grafo, clave) for clave in claves]
    return puntos, distancia


# ----------------------------------------------------------------------
# 2. Indicaciones en español
# ----------------------------------------------------------------------
def direccion_cardinal(desde, hacia):
    """Dice si vamos al norte, sur, este u oeste (según el eje que más cambia)."""
    dx = hacia["x"] - desde["x"]
    dz = hacia["z"] - desde["z"]
    if abs(dx) >= abs(dz):
        return "este" if dx > 0 else "oeste"
    return "sur" if dz > 0 else "norte"


def tipo_de_giro(anterior, actual, siguiente):
    """
    Devuelve "derecha", "izquierda" o "recto".

    Usamos el PRODUCTO CRUZ de dos vectores:
        tramo 1 = de 'anterior' a 'actual'
        tramo 2 = de 'actual' a 'siguiente'
    Si el resultado es positivo, el giro es a la derecha; si es negativo,
    a la izquierda; si es casi cero, vamos recto.
    """
    tramo1_x = actual["x"] - anterior["x"]
    tramo1_z = actual["z"] - anterior["z"]
    tramo2_x = siguiente["x"] - actual["x"]
    tramo2_z = siguiente["z"] - actual["z"]

    largo1 = math.hypot(tramo1_x, tramo1_z)
    largo2 = math.hypot(tramo2_x, tramo2_z)
    if largo1 == 0 or largo2 == 0:
        return "recto"

    # Dividimos para que el resultado quede entre -1 y 1 (es el seno del ángulo).
    seno = (tramo1_x * tramo2_z - tramo1_z * tramo2_x) / (largo1 * largo2)

    if abs(seno) < UMBRAL_GIRO:
        return "recto"
    if seno > 0:
        return "derecha"
    return "izquierda"


def simplificar_camino(camino):
    """
    Quita los puntos de calle (pasillos "C-..." que crea cargar_campus, uno
    cada 10 m) donde se sigue recto. Así quedan solo los giros y las
    indicaciones no se repiten. Los pasillos hechos a mano en el admin, las
    zonas, el primero y el último punto siempre se quedan.
    """
    if len(camino) <= 2:
        return camino
    resultado = [camino[0]]
    for i in range(1, len(camino) - 1):
        actual, siguiente = camino[i], camino[i + 1]
        if siguiente["clave"] == CLAVE_DESTINO:
            # La zona justo antes del destino solo sirve si está a 1 m o más
            if distancia_entre(actual, siguiente) >= 1:
                resultado.append(actual)
        elif not actual["clave"].startswith(PREFIJO_CALLE):
            resultado.append(actual)  # Pasillo del admin o zona: se respeta
        elif distancia_entre(resultado[-1], actual) < TRAMO_MINIMO:
            continue  # Saltitos de pocos metros en los cruces de calles
        elif tipo_de_giro(resultado[-1], actual, siguiente) != "recto":
            resultado.append(actual)
    resultado.append(camino[-1])
    return resultado


def generar_instrucciones(camino, destino):
    """Crea una indicación (texto) por cada punto del camino."""
    if len(camino) == 1:
        return [f"Ya estás en {destino.nombre}."]

    primero = camino[0]
    segundo = camino[1]
    metros = distancia_entre(primero, segundo)
    hacia = direccion_cardinal(primero, segundo)
    indicaciones = [f"Desde {primero['nombre']}, camina {metros:.0f} m hacia el {hacia}."]

    # Puntos intermedios: todos menos el primero y el último.
    for i in range(1, len(camino) - 1):
        anterior = camino[i - 1]
        actual = camino[i]
        siguiente = camino[i + 1]
        metros = distancia_entre(actual, siguiente)
        giro = tipo_de_giro(anterior, actual, siguiente)

        if siguiente["clave"] == CLAVE_DESTINO:
            texto = f"En {actual['nombre']}, busca «{destino.nombre}» ({metros:.0f} m)."
        elif giro == "recto":
            texto = f"Al pasar por {actual['nombre']}, continúa recto {metros:.0f} m."
        else:
            texto = f"En {actual['nombre']}, gira a la {giro} y avanza {metros:.0f} m."
        indicaciones.append(texto)

    indicaciones.append(f"¡Llegaste a {destino.nombre}!")
    return indicaciones


# ----------------------------------------------------------------------
# 3. Armar el grafo con los datos de la base de datos
# ----------------------------------------------------------------------
def obtener_pasillos_y_conexiones():
    """
    Pasillos y conexiones del campus.

    Usa los registrados en el admin. Si todavía no hay ninguno, usa los
    valores por defecto de mapa_campus.py para que la app funcione igual.

    Returns:
        pasillos:   [(codigo, nombre, lat, lng), ...]
        conexiones: [(codigo_a, codigo_b, distancia_m o None), ...]
    """
    pasillos = []
    for pasillo in Pasillo.objects.all():
        pasillos.append((pasillo.codigo, pasillo.nombre, pasillo.latitud, pasillo.longitud))

    if not pasillos:
        conexiones_por_defecto = [(a, b, None) for a, b in CONEXIONES_PASILLOS]
        return list(PASILLOS), conexiones_por_defecto

    conexiones = []
    for conexion in Conexion.objects.select_related("pasillo_a", "pasillo_b"):
        conexiones.append(
            (conexion.pasillo_a.codigo, conexion.pasillo_b.codigo, conexion.distancia_m)
        )
    return pasillos, conexiones


def construir_grafo(zonas, destino):
    """
    Arma el grafo en 3 pasos:
        1. Pasillos y sus conexiones.
        2. Zonas, cada una unida a sus pasillos más cercanos.
        3. El destino, unido a la zona donde está.
    """
    grafo = nx.Graph()
    pasillos, conexiones = obtener_pasillos_y_conexiones()

    # Paso 1: pasillos
    claves_pasillos = []
    for clave, nombre, lat, lng in pasillos:
        agregar_punto(grafo, crear_punto(clave, nombre, lat, lng))
        claves_pasillos.append(clave)
    for clave_a, clave_b, distancia in conexiones:
        conectar(grafo, clave_a, clave_b, distancia)

    # Paso 2: zonas
    for zona in zonas:
        punto_zona = crear_punto(f"Z{zona.pk}", zona.nombre, zona.latitud, zona.longitud)
        agregar_punto(grafo, punto_zona)

        # Ordenamos los pasillos del más cercano al más lejano y tomamos los primeros.
        def distancia_a_la_zona(clave_pasillo):
            return distancia_entre(punto_zona, obtener_punto(grafo, clave_pasillo))

        cercanos = sorted(claves_pasillos, key=distancia_a_la_zona)[:PASILLOS_POR_ZONA]
        for clave_pasillo in cercanos:
            conectar(grafo, punto_zona["clave"], clave_pasillo)

    # Paso 3: destino
    punto_destino = crear_punto(CLAVE_DESTINO, destino.nombre, destino.latitud, destino.longitud)
    agregar_punto(grafo, punto_destino)
    conectar(grafo, CLAVE_DESTINO, f"Z{destino.zona_id}")
    return grafo


# ----------------------------------------------------------------------
# 4. Funciones que usan las vistas, el admin y los serializers
# ----------------------------------------------------------------------
def calcular_camino(origen, destino):
    """
    Camino más corto desde una zona (origen) hasta un destino.

    Returns:
        (waypoints, distancia_en_metros)
        cada waypoint es {"lat": ..., "lng": ..., "instruccion": "..."}
    """
    grafo = construir_grafo(Zona.objects.all(), destino)
    camino, distancia = camino_mas_corto(grafo, f"Z{origen.pk}", CLAVE_DESTINO)
    camino = simplificar_camino(camino)
    indicaciones = generar_instrucciones(camino, destino)

    waypoints = []
    for punto, instruccion in zip(camino, indicaciones):
        lat, lng = a_coordenadas(punto["x"], punto["z"], LAT_REFERENCIA, LNG_REFERENCIA)
        waypoints.append({"lat": lat, "lng": lng, "instruccion": instruccion})
    return waypoints, round(distancia, 1)


def asegurar_camino(ruta, forzar=False):
    """
    Si la Ruta no tiene camino o distancia guardados, los calcula y guarda.
    Con forzar=True los recalcula siempre (botón "Recalcular" del admin).
    """
    falta_camino = not ruta.camino_json
    falta_distancia = ruta.distancia is None

    if not forzar and not falta_camino and not falta_distancia:
        return ruta  # Ya está completa, no hacemos nada.

    waypoints, distancia = calcular_camino(ruta.origen, ruta.destino)
    if forzar or falta_camino:
        ruta.camino_json = waypoints
    if forzar or falta_distancia:
        ruta.distancia = distancia
    if ruta.pk:
        ruta.save(update_fields=["camino_json", "distancia"])
    return ruta


def construir_escena(ruta):
    """
    Datos para la escena 3D (simulacion.js y Unity), en metros.
    X = este, Z = sur, medidos desde LAT_REFERENCIA / LNG_REFERENCIA, que es
    el centro del modelo 3D del campus (en Unity: x = X, z = -Z).
    """

    def a_metros(lat, lng):
        x, z = a_metros_locales(lat, lng, LAT_REFERENCIA, LNG_REFERENCIA)
        # Sumar 0.0 convierte -0.0 en 0.0 (solo para que el JSON se vea limpio).
        return round(x, 2) + 0.0, round(z, 2) + 0.0

    zonas = []
    for zona in Zona.objects.all():
        x, z = a_metros(zona.latitud, zona.longitud)
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
        x, z = a_metros(punto["lat"], punto["lng"])
        camino.append({"x": x, "z": z, "instruccion": punto.get("instruccion", "")})

    # "destino" lo usa Unity para buscar el lugar en el campus 3D (ej: "Aula K-301").
    return {"destino": ruta.destino.nombre, "zonas": zonas, "camino": camino}
