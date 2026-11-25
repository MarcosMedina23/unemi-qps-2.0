"""
Grupos de zonas para la IA (YOLO + Roboflow).

Algunas zonas están tan cerca que en una foto casi siempre salen juntas, así
que el modelo las aprende como UNA sola clase. Esto solo afecta al
reconocimiento por foto: el mapa del GPS, las rutas y los destinos siguen igual.

    GRUPOS_IA  clase de Roboflow -> {"zona": zona principal (la que se devuelve),
                                     "incluye": lugares que abarca esa clase,
                                     "cerca": lugares cercanos (solo información)}
    CERCA_DE   zona -> lugares cercanos que NO están en el mapa (no tenemos su
               ubicación exacta, por eso no se crean como zonas ni destinos).

Los nombres de clase se comparan con zonas.views.clave_nombre (sin tildes,
signos ni mayúsculas): "Bloques V-W-X" == "bloques v w x".
"""

GRUPOS_IA = {
    "Bloques V-W-X": {
        "zona": "Bloque W",
        "incluye": ["Bloque V", "Bloque W", "Bloque X"],
        "cerca": [],
    },
    "Bloque H": {
        "zona": "Bloque H",
        "incluye": ["Bloque H", "Bar del Bloque H", "Entrada peatonal"],
        "cerca": [],
    },
    "Estadio Universitario UNEMI": {
        "zona": "Estadio Universitario UNEMI",
        "incluye": ["Estadio Universitario UNEMI", "Polideportivo", "Bar del polideportivo", "Canchas"],
        "cerca": [],
    },
    "Piscina UNEMI": {
        "zona": "Piscina UNEMI",
        "incluye": ["Piscina UNEMI", "Gimnasio", "Monumento de las Banderas"],
        "cerca": [],
    },
}

CERCA_DE = {
    "Bloque N": ["Baño", "Bar"],
}


def _buscar(diccionario, nombre):
    """(clave original, valor) cuyo nombre coincide ignorando tildes y signos."""
    from .views import clave_nombre  # import local: views importa este módulo

    clave = clave_nombre(nombre or "")
    return next(((k, v) for k, v in diccionario.items() if clave_nombre(k) == clave), (None, None))


def grupo_de_clase(nombre):
    """Grupo de la IA al que pertenece la clase, o (None, None)."""
    return _buscar(GRUPOS_IA, nombre)


def info_grupo(nombre):
    """
    Bloque "grupo" para la respuesta de /api/zonas/reconocer/:
    {"clase": ..., "incluye": [...], "cerca": [...]} o None si no aplica.
    """
    clase, grupo = grupo_de_clase(nombre)
    if grupo is not None:
        cerca = list(grupo["cerca"])
        _, extra = _buscar(CERCA_DE, grupo["zona"])
        cerca += [c for c in extra or [] if c not in cerca]
        return {"clase": clase, "incluye": list(grupo["incluye"]), "cerca": cerca}
    zona, cerca = _buscar(CERCA_DE, nombre)
    if cerca is not None:
        return {"clase": zona, "incluye": [], "cerca": list(cerca)}
    return None
