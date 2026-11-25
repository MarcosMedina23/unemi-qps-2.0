"""
Genera  backend/web/static/web/data/campus_unemi.json  a partir de campus_data.py.

Ese JSON lo usan:
  - la web (simulacion.js) para dibujar el MISMO campus 3D que Unity,
  - Django (python manage.py cargar_campus) para crear las zonas, destinos,
    pasillos (calles) y rutas.

Coordenadas en metros, igual que Unity: X = Este, Z = Norte.
Se ejecuta solo desde gen_cs.py (o a mano: python herramientas\\gen_web.py).
"""
import json
import math
import os

from campus_data import (ARCOS, AREAS, CALLES, EDIFICIOS, ENTRADAS, ESTADIO, ESTERO, L,
                         MONUMENTO, colores, m)

PASO_METROS = 10       # cada cuánto se pone un punto (pasillo) en las calles
DISTANCIA_CRUCE = 11   # puntos de calles distintas más cerca que esto se conectan
METROS_AFUERA = 1.5    # la "puerta" queda 1.5 m afuera de la pared

# Nombre, tipo de destino y descripción de cada lugar que aparece en la lista "¿A dónde vas?".
# id del campus: (nombre en la web, tipo, descripción)
LUGARES = {
    "B": ("Bloque B", "bloque", "Bloque del campus"),
    "C": ("Bloque C", "bloque", "Bloque del campus"),
    "E": ("Bloque E", "bloque", "Bloque del campus"),
    "ED_H_N": ("Bloque F", "bloque", "Bloque del campus"),   # anexo norte del Bloque H
    "H": ("Bloque H", "bloque", "Bloque del campus"),
    "I": ("Bloque I", "bloque", "Bloque del campus"),
    "J": ("Bloque J", "bloque", "Bloque del campus"),
    "K": ("Bloque K", "bloque", "Bloque del campus"),
    "ED_M_N": ("Bloque L", "bloque", "Bloque del campus"),   # anexo norte del Bloque M
    "M": ("Bloque M", "bloque", "Bloque del campus"),
    "N": ("Bloque N", "bloque", "Bloque del campus"),
    "O": ("Bloque O", "bloque", "Bloque del campus"),
    "P": ("Bloque P", "bloque", "Bloque del campus"),
    "R": ("Bloque R", "bloque", "Bloque del campus"),
    "S": ("Bloque S", "bloque", "Bloque del campus"),
    "T": ("Bloque T (FACI)", "bloque", "Facultad de Ciencias e Ingeniería"),
    "U": ("Bloque U", "bloque", "Bloque del campus"),
    "V": ("Bloque V", "bloque", "Bloque del campus"),
    "W": ("Bloque W", "bloque", "Bloque del campus"),
    "X": ("Bloque X", "bloque", "Bloque del campus"),
    "CDIP": ("CDIP", "bloque", "Centro de Desarrollo e Innovación"),
    "SIM": ("SIM", "bloque", "Bloque del campus"),
    "POSGRADO": ("Posgrado", "bloque", "Bloque de Posgrado"),
    "CRAI": ("CRAI", "biblioteca", "Biblioteca (CRAI)"),
    "BIOTEC": ("Bloque de Investigación de Biotecnología", "bloque", "Investigación"),
    "ED_B_N": ("Edificio anexo (Bloque B)", "edificio", "Edificio del campus"),
    "ED_C_O": ("Edificio anexo (Bloque C)", "edificio", "Edificio del campus"),
    "ED_POSG": ("Edificio anexo (Posgrado)", "edificio", "Edificio del campus"),
    "BANOS_1": ("Baños (Bloque K)", "bano", "Baños"),
    "BANOS_2": ("Baños (Bloque E)", "bano", "Baños"),
    "BANOS_3": ("Baños (Canchas)", "bano", "Baños"),
    "PISCINA": ("Piscina UNEMI", "deportivo", "Área deportiva"),
    "CANCHA3": ("Canchas", "deportivo", "Área deportiva"),
    "ESTADIO": ("Estadio Universitario UNEMI", "deportivo", "Área deportiva"),
    "PARQ1": ("Estacionamiento 1", "estacionamiento", "Estacionamiento"),
    "PARQ2": ("Estacionamiento 2", "estacionamiento", "Estacionamiento"),
    "VERDE1": ("Área verde (Bloques R-U)", "area_verde", "Área verde"),
    "VERDE2": ("Área verde sur", "area_verde", "Área verde"),
    "ENTRADA_PEATONAL": ("Entrada peatonal", "acceso", "Acceso al campus"),
    "ENTRADA_VEHICULOS": ("Entrada de vehículos", "acceso", "Acceso al campus"),
    "SALIDA_VEHICULOS": ("Salida de vehículos", "acceso", "Acceso al campus"),
    "MONUMENTO": ("Monumento de las Banderas", "lugar", "Monumento"),
}

# Aulas dentro de un bloque: (nombre, tipo, id del bloque)
AULAS = [("Aula K-301", "aula", "K")]


def redondear(valor):
    return round(valor, 2)


# --------------------------------------------------------------------------
# Grafo de calles (los pasillos de Django)
# --------------------------------------------------------------------------
def armar_grafo():
    """
    Parte cada calle en puntos cada PASO_METROS y conecta calles que se cruzan.
    La Avenida 17 de Septiembre no entra: está fuera del campus y el peatón no
    debe caminar por ella.
    """
    nodos, calle_de_nodo, aristas = [], [], []
    for numero, (nombre, _ancho, estilo, puntos_px) in enumerate(CALLES):
        if estilo == "avenida":
            continue
        puntos = [m(*p) for p in puntos_px]
        nodos.append(puntos[0])
        calle_de_nodo.append(numero)
        for a, b in zip(puntos, puntos[1:]):
            pasos = max(1, math.ceil(math.dist(a, b) / PASO_METROS))
            for k in range(1, pasos + 1):
                nodos.append((a[0] + (b[0] - a[0]) * k / pasos, a[1] + (b[1] - a[1]) * k / pasos))
                calle_de_nodo.append(numero)
                aristas.append((len(nodos) - 2, len(nodos) - 1))

    for i in range(len(nodos)):
        for j in range(i + 1, len(nodos)):
            if calle_de_nodo[i] != calle_de_nodo[j] and math.dist(nodos[i], nodos[j]) <= DISTANCIA_CRUCE:
                aristas.append((i, j))
    return nodos, calle_de_nodo, aristas


# --------------------------------------------------------------------------
# Puerta de cada lugar: el borde del edificio más cercano a la calle
# --------------------------------------------------------------------------
def puerta_rectangulo(cx, cz, ancho, largo, rot, calle):
    """Punto del borde del rectángulo más cercano a 'calle', 1.5 m hacia afuera."""
    t = math.radians(rot)
    # Calle en coordenadas locales del edificio (rotación horaria, igual que Unity)
    dx, dz = calle[0] - cx, calle[1] - cz
    lx = dx * math.cos(t) - dz * math.sin(t)
    lz = dx * math.sin(t) + dz * math.cos(t)
    mx, mz = ancho / 2 + METROS_AFUERA, largo / 2 + METROS_AFUERA
    px, pz = max(-mx, min(mx, lx)), max(-mz, min(mz, lz))
    if abs(px) < mx and abs(pz) < mz:          # la calle está "dentro": se va al lado más cercano
        if mx - abs(px) < mz - abs(pz):
            px = math.copysign(mx, px or 1)
        else:
            pz = math.copysign(mz, pz or 1)
    return (cx + px * math.cos(t) + pz * math.sin(t), cz - px * math.sin(t) + pz * math.cos(t))


def puerta_arco(cx, cz, r_in, r_out, a0, a1, calle):
    """Punto del arco (lado interior o exterior) más cercano a la calle."""
    angulo = math.degrees(math.atan2(calle[1] - cz, calle[0] - cx))
    angulo = max(a0, min(a1, angulo))
    mejor = None
    for radio in (r_in - METROS_AFUERA, r_out + METROS_AFUERA):
        p = (cx + radio * math.cos(math.radians(angulo)), cz + radio * math.sin(math.radians(angulo)))
        if mejor is None or math.dist(p, calle) < math.dist(mejor, calle):
            mejor = p
    return mejor


def main():
    col = colores()
    nodos, calle_de_nodo, aristas = armar_grafo()

    def calle_mas_cercana(punto):
        return min(nodos, key=lambda n: math.dist(n, punto))

    datos = {"edificios": [], "arcos": [], "areas": [], "accesos": [], "calles": [], "lugares": []}
    puertas = {}

    for (i, n, t, cx, cy, w, d, r, h, _e) in EDIFICIOS:
        x, z = m(cx, cy)
        datos["edificios"].append({"id": i, "nombre": n, "tipo": t, "x": x, "z": z, "ancho": L(w),
                                   "largo": L(d), "rot": r, "alto": h, "color": col[i]})
        puertas[i] = puerta_rectangulo(x, z, L(w), L(d), r, calle_mas_cercana((x, z)))

    for (i, n, cx, cy, ri, ro, a0, a1, h, _e) in ARCOS:
        x, z = m(cx, cy)
        datos["arcos"].append({"id": i, "nombre": n, "cx": x, "cz": z, "r_in": L(ri), "r_out": L(ro),
                               "a0": a0, "a1": a1, "alto": h, "color": col[i]})
        medio = math.radians((a0 + a1) / 2)
        centro = (x + L(ri + ro) / 2 * math.cos(medio), z + L(ri + ro) / 2 * math.sin(medio))
        puertas[i] = puerta_arco(x, z, L(ri), L(ro), a0, a1, calle_mas_cercana(centro))

    for (i, n, t, cx, cy, w, d, r, estilo) in AREAS:
        x, z = m(cx, cy)
        datos["areas"].append({"id": i, "nombre": n, "tipo": t, "x": x, "z": z, "ancho": L(w),
                               "largo": L(d), "rot": r, "estilo": estilo})
        puertas[i] = (x, z)

    i, n, cx, cy, w, d, r = ESTADIO
    x, z = m(cx, cy)
    datos["estadio"] = {"id": i, "nombre": n, "x": x, "z": z, "ancho": L(w), "largo": L(d), "rot": r}
    puertas[i] = (x, z)

    for (i, n, t, cx, cy) in ENTRADAS:
        x, z = m(cx, cy)
        datos["accesos"].append({"id": i, "nombre": n, "tipo": t, "x": x, "z": z})
        puertas[i] = (x, z)

    i, n, cx, cy = MONUMENTO
    x, z = m(cx, cy)
    datos["monumento"] = {"id": i, "nombre": n, "x": x, "z": z}
    puertas[i] = (x, z)

    for (n, ancho, estilo, puntos) in CALLES:
        datos["calles"].append({"nombre": n, "ancho": ancho, "estilo": estilo,
                                "puntos": [list(m(*p)) for p in puntos]})
    n, ancho, puntos = ESTERO
    datos["estero"] = {"nombre": n, "ancho": ancho, "puntos": [list(m(*p)) for p in puntos]}

    # Lugares que salen en la lista de destinos (con su puerta)
    for id_, (nombre, tipo, descripcion) in LUGARES.items():
        px, pz = puertas[id_]
        datos["lugares"].append({"id": id_, "nombre": nombre, "tipo": tipo, "descripcion": descripcion,
                                 "x": redondear(px), "z": redondear(pz)})
    datos["aulas"] = [{"nombre": n, "tipo": t, "bloque": LUGARES[b][0]} for (n, t, b) in AULAS]

    # Pasillos con un nombre que se entiende en las indicaciones
    referencias = [(LUGARES[k][0], puertas[k]) for k in LUGARES]
    pasillos = []
    for indice, nodo in enumerate(nodos):
        nombre_calle, _a, estilo, _p = CALLES[calle_de_nodo[indice]]
        if nombre_calle:
            nombre = nombre_calle
        else:
            cercano = min(referencias, key=lambda r: math.dist(r[1], nodo))[0]
            tipo = {"sendero": "Sendero", "peatonal": "Paseo peatonal"}.get(estilo, "Calle")
            nombre = f"{tipo} frente a {cercano}"
        pasillos.append({"x": redondear(nodo[0]), "z": redondear(nodo[1]), "nombre": nombre})
    datos["grafo"] = {"pasillos": pasillos, "conexiones": aristas}

    raiz = os.path.dirname(os.path.abspath(__file__))
    destino = os.path.normpath(os.path.join(raiz, "..", "..", "backend", "web", "static", "web",
                                            "data", "campus_unemi.json"))
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "w", encoding="utf-8", newline="\n") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, separators=(",", ":"))
    print("Generado:", destino, f"({len(pasillos)} pasillos, {len(aristas)} conexiones, "
          f"{len(datos['lugares'])} lugares)")


if __name__ == "__main__":
    main()
