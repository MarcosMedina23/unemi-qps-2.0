-- ============================================================
-- UNEMI Guide AI · Esquema de la base de datos (SQLite)
--
-- Documenta las tablas propias del proyecto, tal como las crea Django
-- con "python manage.py migrate" (generado con "manage.py sqlmigrate").
--
-- NO hace falta ejecutar este archivo: migrate crea estas tablas y
-- también las de Django (auth, sesiones, admin). Sirve como referencia
-- para el informe y para revisar el modelo de datos.
-- ============================================================

-- ------------------------------------------------------------
-- usuarios_usuario: cuentas creadas por el administrador
-- (extiende el usuario de Django con es_estudiante, carrera, semestre)
-- ------------------------------------------------------------
CREATE TABLE "usuarios_usuario" (
    "id"            integer      NOT NULL PRIMARY KEY AUTOINCREMENT,
    "password"      varchar(128) NOT NULL,          -- Hash PBKDF2, nunca texto plano
    "last_login"    datetime     NULL,
    "is_superuser"  bool         NOT NULL,
    "username"      varchar(150) NOT NULL UNIQUE,
    "first_name"    varchar(150) NOT NULL,
    "last_name"     varchar(150) NOT NULL,
    "email"         varchar(254) NOT NULL,
    "is_staff"      bool         NOT NULL,          -- Estudiantes: siempre 0
    "is_active"     bool         NOT NULL,
    "date_joined"   datetime     NOT NULL,
    "es_estudiante" bool         NOT NULL,
    "carrera"       varchar(120) NOT NULL,
    "semestre"      smallint unsigned NULL CHECK ("semestre" >= 0)
);

-- ------------------------------------------------------------
-- zonas_zona: áreas del campus que reconoce la visión artificial
-- ------------------------------------------------------------
CREATE TABLE "zonas_zona" (
    "id"                integer      NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nombre"            varchar(100) NOT NULL UNIQUE,  -- Igual a la clase de YOLO
    "descripcion"       varchar(200) NOT NULL,
    "latitud"           decimal      NOT NULL,
    "longitud"          decimal      NOT NULL,
    "imagen_referencia" varchar(100) NOT NULL          -- Ruta dentro de media/zonas/
);

-- ------------------------------------------------------------
-- zonas_destino: lugares dentro de cada zona
-- tipo: 'aula' | 'laboratorio' | 'biblioteca' | 'oficina'
-- ------------------------------------------------------------
CREATE TABLE "zonas_destino" (
    "id"       integer      NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nombre"   varchar(120) NOT NULL,
    "tipo"     varchar(20)  NOT NULL,
    "latitud"  decimal      NOT NULL,
    "longitud" decimal      NOT NULL,
    "zona_id"  bigint       NOT NULL REFERENCES "zonas_zona" ("id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "destino_unico_por_zona" UNIQUE ("zona_id", "nombre")
);
CREATE INDEX "zonas_destino_zona_id_daa6c4bf" ON "zonas_destino" ("zona_id");

-- ------------------------------------------------------------
-- rutas_pasillo: puntos de cruce del campus (nodos del grafo)
-- ------------------------------------------------------------
CREATE TABLE "rutas_pasillo" (
    "id"       integer      NOT NULL PRIMARY KEY AUTOINCREMENT,
    "codigo"   varchar(10)  NOT NULL UNIQUE,         -- Ej.: P-01
    "nombre"   varchar(100) NOT NULL,
    "latitud"  decimal      NOT NULL,
    "longitud" decimal      NOT NULL
);

-- ------------------------------------------------------------
-- rutas_conexion: caminos entre pasillos (aristas del grafo)
-- distancia_m NULL => se calcula en línea recta al guardar
-- ------------------------------------------------------------
CREATE TABLE "rutas_conexion" (
    "id"           integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "distancia_m"  real    NULL,
    "pasillo_a_id" bigint  NOT NULL REFERENCES "rutas_pasillo" ("id") DEFERRABLE INITIALLY DEFERRED,
    "pasillo_b_id" bigint  NOT NULL REFERENCES "rutas_pasillo" ("id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "conexion_unica" UNIQUE ("pasillo_a_id", "pasillo_b_id"),
    CONSTRAINT "conexion_entre_pasillos_distintos" CHECK (NOT ("pasillo_a_id" = ("pasillo_b_id")))
);
CREATE INDEX "rutas_conexion_pasillo_a_id_14d6c241" ON "rutas_conexion" ("pasillo_a_id");
CREATE INDEX "rutas_conexion_pasillo_b_id_3406e716" ON "rutas_conexion" ("pasillo_b_id");

-- ------------------------------------------------------------
-- rutas_ruta: rutas registradas por el administrador
-- distancia NULL o camino_json '[]' => se calculan solos (Dijkstra)
-- ------------------------------------------------------------
CREATE TABLE "rutas_ruta" (
    "id"          integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "distancia"   real    NULL,                     -- Metros
    "camino_json" text    NOT NULL CHECK ((JSON_VALID("camino_json") OR "camino_json" IS NULL)),
    "destino_id"  bigint  NOT NULL REFERENCES "zonas_destino" ("id") DEFERRABLE INITIALLY DEFERRED,
    "origen_id"   bigint  NOT NULL REFERENCES "zonas_zona" ("id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "ruta_unica_por_par" UNIQUE ("origen_id", "destino_id")
);
CREATE INDEX "rutas_ruta_destino_id_49e64490" ON "rutas_ruta" ("destino_id");
CREATE INDEX "rutas_ruta_origen_id_f4a04e29" ON "rutas_ruta" ("origen_id");

-- ------------------------------------------------------------
-- rutas_historial: consultas guardadas por cada estudiante
-- ------------------------------------------------------------
CREATE TABLE "rutas_historial" (
    "id"          integer      NOT NULL PRIMARY KEY AUTOINCREMENT,
    "fecha"       datetime     NOT NULL,
    "foto_origen" varchar(100) NOT NULL,            -- Ruta dentro de media/historial/
    "usuario_id"  bigint       NOT NULL REFERENCES "usuarios_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
    "ruta_id"     bigint       NOT NULL REFERENCES "rutas_ruta" ("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX "rutas_historial_usuario_id_cc912958" ON "rutas_historial" ("usuario_id");
CREATE INDEX "rutas_historial_ruta_id_da03f3f4" ON "rutas_historial" ("ruta_id");
