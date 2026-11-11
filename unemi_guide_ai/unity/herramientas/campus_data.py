# Fuente única de datos del campus UNEMI.
# Coordenadas medidas en PÍXELES sobre el plano de la primera captura (1077 x 1600).
# Se convierten a metros de Unity: X = Este, Z = Norte.
# Rotación en grados, positiva = sentido horario visto desde arriba (igual que el eje Y de Unity).
#
# Estilo / color de cada edificio:
#   "auto"      -> color único asignado de la paleta
#   "bano"      -> color común de los baños
#   "destacado" -> naranja (Bloque K)
#   "=ID"       -> mismo color que el edificio ID (partes de un mismo edificio)
#   "#RRGGBB"   -> color fijo

S = 0.45            # metros por píxel del plano
OX, OY = 540, 1000  # píxel que será el origen (0,0,0) de Unity

def m(px, py):
    return round((px - OX) * S, 2), round((OY - py) * S, 2)

def L(v):
    return round(v * S, 2)

# ---------------- Edificios (cajas) ----------------
# id, nombre visible, tipo, cx, cy, ancho(px), largo(px), rot, alto(m), estilo
EDIFICIOS = [
    ("POSGRADO", "Posgrado",            "Bloque",   422, 735, 80, 45, 10, 9,  "auto"),
    ("SIM",      "SIM",                 "Bloque",   497, 808, 50, 35, 15, 7,  "auto"),
    ("CDIP",     "CDIP",                "Bloque",   370, 908, 125, 170, 6, 12, "auto"),
    ("CRAI",     "CRAI",                "Bloque",   522, 940, 95, 55, 0, 10,  "auto"),
    ("CRAI_N",   "",                    "Edificio", 522, 905, 45, 40, 0, 10,  "=CRAI"),
    ("R",        "Bloque R",            "Bloque",   327, 1075, 55, 55, 5, 9,  "auto"),
    ("ED_M_N",   "",                    "Edificio", 480, 1055, 75, 35, 5, 8,  "auto"),
    ("M",        "Bloque M",            "Bloque",   455, 1120, 85, 40, 5, 9,  "auto"),
    ("N",        "Bloque N",            "Bloque",   450, 1195, 80, 35, 5, 9,  "auto"),
    ("S",        "Bloque S",            "Bloque",   330, 1170, 65, 45, 5, 9,  "auto"),
    ("T",        "Bloque T (FACI)",     "Bloque",   298, 1240, 70, 40, 8, 9,  "auto"),
    ("U",        "Bloque U",            "Bloque",   278, 1340, 70, 55, 8, 9,  "auto"),
    ("O",        "Bloque O",            "Bloque",   420, 1310, 60, 40, 5, 9,  "auto"),
    ("P",        "Bloque P",            "Bloque",   425, 1395, 55, 40, 5, 9,  "auto"),
    ("J",        "Bloque J",            "Bloque",   515, 1385, 80, 40, 5, 9,  "auto"),
    ("K",        "Bloque K",            "Bloque",   553, 1432, 90, 35, 5, 12, "destacado"),
    ("BANOS_1",  "Baños",               "Servicio", 467, 1447, 60, 25, 5, 4,  "bano"),
    ("I",        "Bloque I",            "Bloque",   540, 1318, 65, 40, 5, 9,  "auto"),
    ("H",        "Bloque H",            "Bloque",   587, 1180, 55, 125, 5, 12, "auto"),
    ("ED_H_N",   "",                    "Edificio", 585, 1105, 40, 20, 5, 6,  "auto"),
    ("B",        "Bloque B",            "Bloque",   683, 1125, 90, 55, 5, 9,  "auto"),
    ("ED_B_N",   "",                    "Edificio", 692, 1082, 65, 28, 5, 6,  "auto"),
    ("C",        "Bloque C",            "Bloque",   690, 1240, 65, 40, 5, 9,  "auto"),
    ("ED_C_O",   "",                    "Edificio", 635, 1245, 25, 25, 5, 5,  "auto"),
    ("E",        "Bloque E",            "Bloque",   695, 1310, 65, 50, 5, 9,  "auto"),
    ("BANOS_2",  "Baños",               "Servicio", 632, 1334, 25, 30, 5, 4,  "bano"),   # punto amarillo del mapa
    ("ED_POSG",  "",                    "Edificio", 540, 740, 30, 30, 17, 5,  "auto"),
    ("BANOS_3",  "Baños",               "Servicio", 678, 872, 25, 40, 17, 4,  "bano"),   # punto amarillo del mapa
    ("BIOTEC",   "Bloque de Investigación de Biotecnología", "Bloque", 640, 300, 110, 80, 0, 10, "auto"),
]

# ---------------- Bloques en arco (V, W, X) ----------------
# id, nombre, centro px, radio interior px, radio exterior px, ángulo inicio, ángulo fin (grados, antihorario desde el Este), alto, estilo
ARCOS = [
    ("V", "Bloque V", 490, 690, 80, 150, 115, 165, 12, "auto"),
    ("W", "Bloque W", 490, 690, 95, 165, 55, 110, 12, "auto"),
    ("X", "Bloque X", 490, 690, 50, 120, -20, 48, 12, "auto"),
]

# ---------------- Áreas planas ----------------
# id, nombre, tipo, cx, cy, ancho px, largo px, rot, estilo
AREAS = [
    ("PISCINA", "Piscina UNEMI", "Deportivo", 717, 620, 118, 198, 17, "agua"),
    ("CANCHA1", "", "Deportivo", 588, 758, 55, 60, 17, "cancha"),
    ("CANCHA2", "", "Deportivo", 635, 772, 45, 60, 17, "cancha"),
    ("CANCHA3", "Canchas", "Deportivo", 678, 790, 45, 55, 17, "cancha"),
    ("CANCHA4", "", "Deportivo", 600, 840, 35, 40, 17, "cancha"),
    ("CANCHA5", "", "Deportivo", 640, 855, 35, 40, 17, "cancha"),
    ("PARQ1", "Estacionamiento 1", "Estacionamiento", 790, 315, 120, 110, 0, "parqueo"),
    ("PARQ2", "Estacionamiento 2", "Estacionamiento", 115, 1470, 230, 200, 26, "parqueo"),
    ("VERDE1", "Área Verde", "AreaVerde", 207, 1170, 80, 290, 12, "verde"),
    ("VERDE2", "Área Verde", "AreaVerde", 440, 1592, 470, 150, 26, "verde"),
]

# ---------------- Estadio (elipse) ----------------
ESTADIO = ("ESTADIO", "Estadio Universitario UNEMI", 850, 805, 255, 400, 19)  # cx, cy, ancho, largo, rot

# ---------------- Accesos ----------------
# id, nombre, tipo, cx, cy
ENTRADAS = [
    ("ENTRADA_PEATONAL", "Entrada peatonal",     "Entrada",          775, 1240),
    ("SALIDA_VEHICULOS", "Salida de vehículos",  "SalidaVehicular",  668, 1465),
    ("ENTRADA_VEHICULOS", "Entrada de vehículos", "EntradaVehicular", 868, 248),
]

# ---------------- Monumento de las banderas ----------------
MONUMENTO = ("MONUMENTO", "Monumento de las Banderas", 772, 415)

# ---------------- Calles y senderos ----------------
# nombre, ancho en metros, estilo, puntos px
CALLES = [
    ("Avenida 17 de Septiembre", 16, "avenida", [(1358, 120), (611, 1730)]),
    ("", 7, "calle", [(180, 545), (340, 345)]),
    ("", 7, "calle", [(180, 545), (250, 600), (330, 660), (350, 720), (340, 795), (300, 1000), (255, 1200), (215, 1360)]),
    ("", 6, "calle", [(340, 795), (470, 800), (640, 880)]),
    ("", 6, "calle", [(465, 745), (440, 1000), (400, 1200), (355, 1420)]),
    ("", 7, "calle", [(290, 995), (520, 1015), (770, 1045), (850, 1045), (1005, 860)]),
    ("", 6, "calle", [(640, 880), (648, 1035)]),
    ("", 6, "calle", [(765, 1045), (760, 1165), (875, 1165)]),
    ("", 7, "calle", [(40, 1285), (650, 1590), (720, 1625)]),
    ("", 6, "calle", [(760, 1165), (748, 1380), (650, 1420), (600, 1520)]),
    # Vía vehicular: entra junto al Estacionamiento 1, pasa por detrás del bloque de Biotecnología
    # y se une con la calle del lado oeste
    ("Vía de acceso vehicular", 7, "calle", [(868, 248), (780, 236), (640, 232), (500, 252), (340, 345)]),
    # Sendero peatonal: Piscina -> Monumento de las Banderas -> Estacionamiento 1 -> vía vehicular
    # (el último tramo cruza el estacionamiento y une el sendero con el resto de calles)
    ("", 3, "sendero", [(746, 527), (772, 415), (788, 372), (783, 240)]),
    # Sendero peatonal SUPUESTO (no estaba en el plano): une la calle del Bloque P con la del
    # Bloque K pasando por debajo de los baños. Sin él, las rutas al K daban la vuelta por la
    # Avenida. Si en el campus real no existe, bórralo y vuelve a ejecutar gen_cs.py.
    ("", 3, "sendero", [(355, 1420), (470, 1478), (600, 1515)]),

    # ---- Paseos peatonales (estilo "peatonal") ----
    # Pasan ENTRE los edificios para que el peatón no tenga que salir a las calles
    # de autos ni a la Avenida. Cada uno se trazó revisando que no cruce ningún bloque.
    # Paseo central norte-sur: entre M/N/ED_M_N (oeste) y H (este)
    ("Paseo central", 4, "peatonal", [(527, 1017), (527, 1275)]),
    # Paseo este-oeste al norte de O, I, C y E (de la calle del Bloque P a la del Bloque C)
    ("Paseo de los bloques", 4, "peatonal", [(385, 1275), (754, 1275)]),
    # Paseo este-oeste entre O-I-E (norte) y P-J-K (sur)
    ("", 4, "peatonal", [(368, 1355), (749, 1355)]),
    # Al este del Bloque K: une el paseo de arriba con la calle del K (J <-> K sin rodeo)
    ("", 4, "peatonal", [(612, 1355), (612, 1496)]),
    # Corto norte-sur entre I y los baños del Bloque E
    ("", 4, "peatonal", [(596, 1275), (596, 1355)]),
    # Entre H (oeste) y B (este), hasta el anexo del Bloque C
    ("", 4, "peatonal", [(627, 1029), (627, 1213)]),
    # Pasillo angosto (2.5 m) entre H y el anexo del Bloque C: une el paseo anterior con
    # el "Paseo de los bloques" (sin él, de H a C había que dar toda la vuelta)
    ("", 2.5, "peatonal", [(627, 1213), (616, 1222), (616, 1275)]),
    # Hacia la Piscina UNEMI: sale de la calle de las canchas y sube entre canchas y estadio
    ("", 4, "peatonal", [(645, 960), (706, 960), (706, 800), (742, 712)]),
]

ESTERO = ("Estero de Belín", 6, [(20, 1150), (68, 1105), (180, 1000), (255, 900), (268, 700),
                                 (290, 600), (330, 545), (420, 505), (735, 425), (900, 470),
                                 (1005, 520), (1060, 560)])

# ---------------- Colores ----------------
PALETA = ["#2E7D32", "#1565C0", "#6A1B9A", "#C62828", "#00838F", "#AD1457", "#4E342E", "#00BFA5",
          "#283593", "#558B2F", "#0277BD", "#00695C", "#8E24AA", "#5D4037", "#1B5E20", "#3949AB",
          "#E53935", "#43A047", "#039BE5", "#7CB342", "#FDD835", "#00ACC1", "#8D6E63", "#5E35B1",
          "#D81B60", "#26A69A", "#9E9D24", "#546E7A", "#EC407A", "#AB47BC", "#29B6F6", "#6D4C41"]
COLOR_DESTACADO = "#F57C00"
COLOR_BANO = "#B0BEC5"

def colores():
    """Devuelve {id: '#RRGGBB'} con un color distinto para cada edificio."""
    res, i = {}, 0
    items = [(e[0], e[9]) for e in EDIFICIOS] + [(a[0], a[9]) for a in ARCOS]
    for id_, est in items:
        if est == "auto":
            res[id_] = PALETA[i % len(PALETA)]; i += 1
        elif est == "bano":
            res[id_] = COLOR_BANO
        elif est == "destacado":
            res[id_] = COLOR_DESTACADO
        elif est.startswith("#"):
            res[id_] = est
    for id_, est in items:
        if est.startswith("="):
            res[id_] = res[est[1:]]
    return res
