r"""
Mapa de pasillos POR DEFECTO del campus.

Lo normal es registrar los pasillos y sus conexiones en el admin
(Rutas e historial → Pasillos del campus). Estos valores solo se usan si
en el admin todavía no hay ningún pasillo, para que la app funcione desde
el primer momento. Son los mismos que carga ``loaddata datos_demo``.

Las ZONAS y DESTINOS se cargan desde el admin. Aquí solo se definen los
PASILLOS (puntos de cruce por donde se camina) y cómo se conectan entre sí.
Cada zona se conecta automáticamente a sus pasillos más cercanos, así que
si el administrador agrega una zona nueva no hace falta tocar este archivo.

Plano aproximado (vista superior, coordenadas de seed_data.sql):

                      Biblioteca Central
                              |
        Bloque B ------ P-03 Pasillo Norte ------ Bloque C
                \             |                  /     |
                 \---- P-01 Plaza Central ------/      |
                              |                        |
                          Bloque A ------------ P-02 Cruce Este
                                                       |
                                              Bloque Administrativo

NOTA: coordenadas aproximadas, pensadas para la demostración. Cuando se
mida el campus real basta con actualizar las tuplas de PASILLOS.
"""

# (clave, nombre, latitud, longitud)
PASILLOS = (
    ("P-01", "Plaza Central", -2.149160, -79.603600),
    ("P-02", "Cruce Este", -2.149700, -79.602925),
    ("P-03", "Pasillo Norte", -2.148756, -79.603600),
)

# Caminos entre pasillos (bidireccionales).
CONEXIONES_PASILLOS = (
    ("P-01", "P-02"),
    ("P-01", "P-03"),
)

# A cuántos pasillos (los más cercanos) se conecta cada zona.
PASILLOS_POR_ZONA = 2
