"""
Decide qué responder al estudiante juntando tres pistas:

    1. La IA (detecciones de la foto, con su confianza).
    2. La calidad de la foto (vision/calidad.py).
    3. El GPS del celular (opcional: solo si dio permiso y la foto es de la cámara).

Resultado de ``decidir()`` (un dict):

    {"motivo": None,               "zona": Zona, "confianza": 0.91}   -> reconocida
    {"motivo": "dudosa",           "opciones": [...], "mensaje": ...}  -> que elija
    {"motivo": "foto_mala",        "opciones": [...], "mensaje": ...}  -> otra foto
    {"motivo": "fuera_del_campus", "opciones": [],    "mensaje": ...}
    {"motivo": "sin_deteccion",    "opciones": [...], "mensaje": ...}

Cada opción es {"zona": Zona, "confianza": float | None, "distancia_m": int | None}.
Siempre se intenta dar la respuesta más acertada: si no se sabe la zona exacta,
se ofrecen las más probables o las que están cerca según el GPS.
"""
from vision.utils import UMBRAL_AMARILLO, UMBRAL_VERDE, distancia_metros

from .grupos_ia import es_clase_sin_zona
from .models import Zona

UMBRAL_OPCION = 0.30            # confianza mínima para ofrecer una zona como opción
MARGEN_DUDA = 0.10              # si la 2.ª zona está así de cerca de la 1.ª, se pregunta
MAX_OPCIONES = 3
PRECISION_GPS_UTIL_M = 100      # con más error, el GPS no se usa para elegir zonas
DISTANCIA_FUERA_CAMPUS_M = 250  # a más de esto de cualquier zona = fuera del campus
DISTANCIA_COHERENTE_M = 150     # zona de la foto más lejos que esto del GPS = no cuadra
RADIO_CERCA_M = 90              # zonas "cerca de ti" según el GPS

MENSAJES = {
    "dudosa": "No estamos seguros de dónde estás. ¿Estás en alguno de estos lugares?",
    "dudosa_gps": "No reconocimos la foto, pero según tu ubicación estás cerca de estos "
                  "lugares. ¿Estás en alguno? Si no, acércate a un bloque y toma otra foto.",
    "foto_mala": "La foto no se ve bien y no pudimos reconocer el lugar.",
    "fuera_del_campus": "Parece que no estás dentro del campus UNEMI. Esta app solo funciona "
                        "dentro de la universidad. Cuando llegues, toma una foto de un bloque "
                        "o letrero.",
    "sin_deteccion": "No reconocemos este lugar como parte del campus UNEMI. Si estás dentro, "
                     "apunta a un bloque, letrero o entrada y vuelve a tomar la foto. Esta app "
                     "solo funciona dentro de la universidad.",
}


class Ubicacion:
    """Posición del celular enviada por la web (latitud, longitud, precisión en metros)."""

    def __init__(self, latitud, longitud, precision):
        self.latitud = float(latitud)
        self.longitud = float(longitud)
        # Si el navegador no dijo la precisión, se supone la de un GPS de celular normal.
        self.precision = max(float(precision), 0.0) if precision is not None else 50.0

    @property
    def util(self):
        """True si el GPS es lo bastante preciso para elegir entre zonas cercanas."""
        return self.precision <= PRECISION_GPS_UTIL_M

    def distancia_a(self, zona):
        return distancia_metros(self.latitud, self.longitud, zona.latitud, zona.longitud)


def candidatos_de_la_foto(resultado, buscar_zona):
    """[(zona, confianza)] sin repetir zonas, de mayor a menor confianza."""
    mejores = {}
    cache = {}

    def anotar(clase, confianza):
        if not clase or es_clase_sin_zona(clase):
            return
        if clase not in cache:
            cache[clase] = buscar_zona(clase)
        zona = cache[clase]
        if zona is not None and confianza > mejores.get(zona.id, (None, -1))[1]:
            mejores[zona.id] = (zona, float(confianza))

    anotar(resultado.get("zona"), resultado.get("confianza") or 0.0)
    for deteccion in resultado.get("detecciones") or []:
        anotar(deteccion.get("clase"), deteccion.get("confianza") or 0.0)
    return sorted(mejores.values(), key=lambda par: par[1], reverse=True)


def opcion(zona, confianza=None, ubicacion=None):
    distancia = round(ubicacion.distancia_a(zona)) if ubicacion else None
    return {"zona": zona, "confianza": confianza, "distancia_m": distancia}


def decidir(resultado, calidad, ubicacion, buscar_zona):
    """Aplica las reglas y devuelve qué responder (ver docstring del módulo)."""
    zonas = list(Zona.objects.all())

    # 1. GPS: ¿está fuera del campus? (aunque el GPS sea impreciso, si está a
    #    kilómetros se nota igual).
    if ubicacion and zonas:
        mas_cercana = min(ubicacion.distancia_a(z) for z in zonas)
        if mas_cercana - ubicacion.precision > DISTANCIA_FUERA_CAMPUS_M:
            return {"motivo": "fuera_del_campus", "opciones": [],
                    "mensaje": MENSAJES["fuera_del_campus"]}

    gps = ubicacion if ubicacion and ubicacion.util else None
    candidatos = candidatos_de_la_foto(resultado, buscar_zona)

    # 2. Con GPS preciso se descartan las zonas que no cuadran con la ubicación.
    if gps:
        limite = DISTANCIA_COHERENTE_M + gps.precision
        candidatos = [(z, c) for z, c in candidatos if gps.distancia_a(z) <= limite]

    # 3. ¿La IA está segura?
    if candidatos:
        zona, confianza = candidatos[0]
        segunda = candidatos[1][1] if len(candidatos) > 1 else 0.0
        hay_empate = segunda >= UMBRAL_OPCION and confianza - segunda < MARGEN_DUDA
        foto_mala_y_dudosa = calidad["nivel"] == "mala" and confianza < UMBRAL_VERDE
        if confianza >= UMBRAL_AMARILLO and not hay_empate and not foto_mala_y_dudosa:
            return {"motivo": None, "zona": zona, "confianza": round(confianza, 2), "opciones": []}

    # 4. No está segura: se ofrecen las zonas más probables y, con GPS, las cercanas.
    opciones = [opcion(z, round(c, 2), gps) for z, c in candidatos if c >= UMBRAL_OPCION]
    opciones = opciones[:MAX_OPCIONES]
    solo_por_gps = not opciones
    if gps:
        ya = {o["zona"].id for o in opciones}
        cercanas = sorted(
            (z for z in zonas if z.id not in ya
             and gps.distancia_a(z) <= RADIO_CERCA_M + gps.precision),
            key=gps.distancia_a,
        )
        opciones += [opcion(z, None, gps) for z in cercanas[:MAX_OPCIONES - len(opciones)]]

    if calidad["nivel"] == "mala":
        motivo, mensaje = "foto_mala", MENSAJES["foto_mala"]
    elif opciones:
        motivo = "dudosa"
        mensaje = MENSAJES["dudosa_gps" if solo_por_gps else "dudosa"]
    else:
        motivo, mensaje = "sin_deteccion", MENSAJES["sin_deteccion"]
    return {"motivo": motivo, "opciones": opciones, "mensaje": mensaje}
