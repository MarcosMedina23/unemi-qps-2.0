-- ============================================================
-- UNEMI Guide AI · Datos de prueba (SQLite)
--
-- Carga 5 zonas, 6 destinos, 3 pasillos, 2 conexiones y 4 rutas.
-- Los USUARIOS no se cargan aquí: créalos en /admin/.
--
-- FORMA RECOMENDADA de cargar estos mismos datos (más simple):
--     python manage.py loaddata datos_demo
-- (usa backend/rutas/fixtures/datos_demo.json)
--
-- Este archivo SQL queda como referencia para el informe. Si igual
-- quieres usarlo (base vacía, después de migrate):
--   python -c "import sqlite3; c=sqlite3.connect('db.sqlite3'); c.executescript(open('../database/seed_data.sql', encoding='utf-8').read()); c.close()"
--
-- Coordenadas aproximadas, solo para la demostración.
-- Las rutas se guardan con distancia NULL y camino '[]': la app las
-- calcula sola (Dijkstra) la primera vez que alguien las consulta.
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 5 zonas. "Bloque A" es la que devuelve el reconocimiento simulado.
-- ------------------------------------------------------------
INSERT INTO zonas_zona (nombre, descripcion, latitud, longitud, imagen_referencia) VALUES
('Bloque A',              'Facultad de Ciencias e Ingeniería', -2.149700, -79.603600, ''),
('Bloque B',              'Facultad de Ciencias Sociales',     -2.149160, -79.604410, ''),
('Bloque C',              'Laboratorios de Computación',       -2.149026, -79.602925, ''),
('Biblioteca Central',    'Biblioteca y salas de estudio',     -2.148351, -79.603600, ''),
('Bloque Administrativo', 'Rectorado y Secretaría General',    -2.149970, -79.602655, '');

-- ------------------------------------------------------------
-- 6 destinos (se buscan por nombre de zona para no depender de ids)
-- ------------------------------------------------------------
INSERT INTO zonas_destino (nombre, tipo, latitud, longitud, zona_id) VALUES
('Aula A-101',          'aula',        -2.149646, -79.603672, (SELECT id FROM zonas_zona WHERE nombre = 'Bloque A')),
('Lab. Computación 3',  'laboratorio', -2.148981, -79.602862, (SELECT id FROM zonas_zona WHERE nombre = 'Bloque C')),
('Lab. Redes',          'laboratorio', -2.148963, -79.602988, (SELECT id FROM zonas_zona WHERE nombre = 'Bloque C')),
('Sala de lectura',     'biblioteca',  -2.148297, -79.603555, (SELECT id FROM zonas_zona WHERE nombre = 'Biblioteca Central')),
('Aula B-204',          'aula',        -2.149106, -79.604464, (SELECT id FROM zonas_zona WHERE nombre = 'Bloque B')),
('Secretaría General',  'oficina',     -2.150024, -79.602601, (SELECT id FROM zonas_zona WHERE nombre = 'Bloque Administrativo'));

-- ------------------------------------------------------------
-- 3 pasillos y 2 conexiones (el grafo de caminos del campus)
-- ------------------------------------------------------------
INSERT INTO rutas_pasillo (codigo, nombre, latitud, longitud) VALUES
('P-01', 'Plaza Central', -2.149160, -79.603600),
('P-02', 'Cruce Este',    -2.149700, -79.602925),
('P-03', 'Pasillo Norte', -2.148756, -79.603600);

INSERT INTO rutas_conexion (pasillo_a_id, pasillo_b_id, distancia_m) VALUES
((SELECT id FROM rutas_pasillo WHERE codigo = 'P-01'), (SELECT id FROM rutas_pasillo WHERE codigo = 'P-02'), 96.1),
((SELECT id FROM rutas_pasillo WHERE codigo = 'P-01'), (SELECT id FROM rutas_pasillo WHERE codigo = 'P-03'), 44.9);

-- ------------------------------------------------------------
-- 4 rutas desde Bloque A. A propósito NO hay ruta hacia
-- "Secretaría General": sirve para probar la pantalla "Sin ruta disponible".
-- ------------------------------------------------------------
INSERT INTO rutas_ruta (origen_id, destino_id, distancia, camino_json)
SELECT z.id, d.id, NULL, '[]'
FROM zonas_zona z, zonas_destino d
WHERE z.nombre = 'Bloque A'
  AND d.nombre IN ('Lab. Computación 3', 'Lab. Redes', 'Sala de lectura', 'Aula B-204');

COMMIT;
