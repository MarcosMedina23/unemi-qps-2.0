"""
python manage.py cargar_campus

Carga el campus UNEMI real (el mismo del modelo 3D de Unity) en la base de datos,
leyendo web/static/web/data/campus_unemi.json (lo genera unity/herramientas/gen_cs.py):

  1. PASILLOS y CONEXIONES = las calles y senderos del campus (un punto cada 10 m).
     Reemplazan a los pasillos que hubiera antes.
  2. ZONAS y DESTINOS = bloques, edificios, baños, canchas, estacionamientos,
     áreas verdes, entrada y salida (cada lugar en su "puerta").
  3. RUTAS = una por cada par zona → destino, para que "Ver ruta" funcione
     con todos. El camino lo calcula Dijkstra la primera vez que se pide.

Se puede ejecutar varias veces: actualiza lo que ya existe sin duplicar.
"""
import json
import math

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from rutas.models import Conexion, Pasillo, Ruta
from rutas.services import LAT_REFERENCIA, LNG_REFERENCIA, PREFIJO_CALLE
from vision.utils import a_coordenadas
from zonas.models import Destino, Zona

ARCHIVO_CAMPUS = settings.BASE_DIR / "web" / "static" / "web" / "data" / "campus_unemi.json"

# Zonas de los datos de prueba (loaddata datos_demo) que se ubican en un lugar real.
#   "Bloque A" de la demo es la Facultad de Ciencias e Ingeniería → Bloque T (FACI).
#   "Biblioteca Central" de la demo es la biblioteca → CRAI.
ZONAS_DEMO = {"Bloque A": "T", "Biblioteca Central": "CRAI"}


def a_lat_lng(x, z_norte):
    """Metros del campus (X = este, Z = norte) → (latitud, longitud)."""
    return a_coordenadas(x, -z_norte, LAT_REFERENCIA, LNG_REFERENCIA)


class Command(BaseCommand):
    help = "Carga los lugares, calles y rutas del campus UNEMI (modelo 3D)."

    @transaction.atomic
    def handle(self, *args, **opciones):
        with open(ARCHIVO_CAMPUS, encoding="utf-8") as archivo:
            campus = json.load(archivo)

        pasillos = self.cargar_pasillos(campus["grafo"])
        zonas = self.cargar_lugares(campus)
        rutas = self.crear_rutas()

        self.stdout.write(self.style.SUCCESS(
            f"Campus cargado: {pasillos} pasillos, {zonas} lugares, {rutas} rutas nuevas."
        ))

    # ------------------------------------------------------------------
    def cargar_pasillos(self, grafo):
        """Borra los pasillos anteriores y crea las calles del campus."""
        Pasillo.objects.all().delete()  # Sus conexiones se borran solas (CASCADE)

        creados = []
        for numero, punto in enumerate(grafo["pasillos"], start=1):
            lat, lng = a_lat_lng(punto["x"], punto["z"])
            creados.append(Pasillo(codigo=f"{PREFIJO_CALLE}{numero:03d}", nombre=punto["nombre"],
                                   latitud=lat, longitud=lng))
        creados = Pasillo.objects.bulk_create(creados)

        conexiones = []
        for a, b in grafo["conexiones"]:
            pa, pb = grafo["pasillos"][a], grafo["pasillos"][b]
            distancia = round(math.hypot(pb["x"] - pa["x"], pb["z"] - pa["z"]), 1)
            conexiones.append(Conexion(pasillo_a=creados[a], pasillo_b=creados[b], distancia_m=distancia))
        Conexion.objects.bulk_create(conexiones)
        return len(creados)

    # ------------------------------------------------------------------
    def cargar_lugares(self, campus):
        """Crea (o actualiza) una zona y un destino por cada lugar del campus."""
        lugares_por_id = {}
        for lugar in campus["lugares"]:
            lat, lng = a_lat_lng(lugar["x"], lugar["z"])
            zona, creada = Zona.objects.get_or_create(
                nombre=lugar["nombre"],
                defaults={"descripcion": lugar["descripcion"], "latitud": lat, "longitud": lng},
            )
            if not creada:
                self.mover(zona, lat, lng)  # Ej.: "Bloque B" de la demo pasa a su lugar real
            Destino.objects.update_or_create(
                zona=zona, nombre=lugar["nombre"],
                defaults={"tipo": lugar["tipo"], "latitud": lat, "longitud": lng},
            )
            lugares_por_id[lugar["id"]] = zona

        # Aulas dentro de un bloque (ej.: Aula K-301 en el Bloque K)
        for aula in campus["aulas"]:
            bloque = Zona.objects.get(nombre=aula["bloque"])
            Destino.objects.update_or_create(
                zona=bloque, nombre=aula["nombre"],
                defaults={"tipo": aula["tipo"], "latitud": bloque.latitud, "longitud": bloque.longitud},
            )

        # Zonas de la demo que corresponden a un lugar real
        for nombre_demo, id_campus in ZONAS_DEMO.items():
            zona = Zona.objects.filter(nombre=nombre_demo).first()
            if zona:
                real = lugares_por_id[id_campus]
                self.mover(zona, real.latitud, real.longitud)
        return len(campus["lugares"])

    @staticmethod
    def mover(zona, lat, lng):
        """Cambia la ubicación de una zona y de los destinos que tiene adentro."""
        zona.latitud, zona.longitud = lat, lng
        zona.save(update_fields=["latitud", "longitud"])
        zona.destinos.update(latitud=lat, longitud=lng)

    # ------------------------------------------------------------------
    def crear_rutas(self):
        """Una ruta por cada zona → destino. Las que ya existían se recalculan."""
        # Los caminos guardados se hicieron con los pasillos viejos: se vacían
        # para que Dijkstra los vuelva a calcular con las calles nuevas.
        Ruta.objects.update(camino_json=[], distancia=None)

        existentes = set(Ruta.objects.values_list("origen_id", "destino_id"))
        nuevas = []
        for zona in Zona.objects.all():
            for destino in Destino.objects.all():
                if destino.nombre == zona.nombre or (zona.pk, destino.pk) in existentes:
                    continue  # No hace falta ruta a la misma zona
                nuevas.append(Ruta(origen=zona, destino=destino))
        Ruta.objects.bulk_create(nuevas)
        return len(nuevas)
