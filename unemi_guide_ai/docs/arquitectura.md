# Arquitectura de UNEMI Guide AI

## 1. Visión general

Es un único proyecto Django que sirve a la vez:
- la **API REST** (`/api/...`);
- la **página única** del estudiante (`/`);
- el **login y la recuperación de cuenta** (`/login/`, `/recuperar/...`);
- el **panel de administración** (`/admin/`).

```text
┌─────────────────────────────── NAVEGADOR ───────────────────────────────┐
│  index.html (10 pantallas)  ·  app.css + 5 CSS  ·  app.js + api.js …    │
│  camera.js (foto)  ruta.js (destinos, mapa)  simulacion.js (Three.js)   │
└──────────────┬───────────────────────────────────────────┬──────────────┘
               │ fetch + cookie de sesión + token CSRF     │ formularios
┌──────────────▼───────────────────────┐   ┌───────────────▼──────────────┐
│ API REST (DRF)  solo con sesión      │   │ web: login, recuperar clave  │
│ zonas/ · rutas/ · usuarios/ (views)  │   │ y usuario (vistas de Django) │
└──────────────┬───────────────────────┘   └──────────────────────────────┘
┌──────────────▼──────────────────────────────────────────────────────────┐
│ SERVICIOS (Python puro)                                                 │
│ vision/services.py  reconocer_zona: simulado · modelo local · ia_service│
│ vision/utils.py     semáforo · validación de fotos · geometría          │
│ rutas/services.py   grafo del campus + Dijkstra + indicaciones + 3D     │
└──────────────┬──────────────────────────────────────────────────────────┘
┌──────────────▼───────────────────────┐   ┌──────────────────────────────┐
│ MODELOS → SQLite (db.sqlite3)        │   │ /admin/: único lugar de carga│
│ Usuario · Zona · Destino · Ruta ·    │◄──┤ usuarios, zonas, destinos,   │
│ Historial                            │   │ rutas (historial: solo ver)  │
└──────────────────────────────────────┘   └──────────────────────────────┘
```

**Principio:** las decisiones se toman en **Python**:
- la zona reconocida y su semáforo;
- el camino más corto y las indicaciones de giro;
- las coordenadas de la escena 3D.

El JavaScript solo **muestra** esos resultados.

---

## 2. Apps de Django

| App | Responsabilidad | Archivos clave |
|---|---|---|
| `usuarios` | Modelo `Usuario` (AbstractUser + es_estudiante, carrera, semestre), ranking de carreras | `models.py`, `admin.py`, `views.py` |
| `zonas` | `Zona`, `Destino`, API de solo lectura y reconocimiento por foto | `models.py`, `views.py`, `serializers.py` |
| `rutas` | `Pasillo`, `Conexion`, `Ruta`, `Historial`, cálculo de ruta, historial y Dijkstra | `services.py`, `models.py`, `fixtures/datos_demo.json` |
| `vision` | Reconocimiento en 3 modos (simulado, modelo local, ia_service) y utilidades | `services.py`, `utils.py` |
| `ml/` (carpeta) | Entrenamiento de YOLOv8 y del clasificador TF-IDF + RandomForest | `entrenar_yolo.py`, `entrenar_clasificador.py` |
| `web` | Página única, login, logout y recuperación de cuenta | `views.py`, `urls.py`, `forms.py`, `templates/`, `static/` |

---

## 3. API REST

Todas las rutas requieren **sesión iniciada**; sin sesión responden 403. No hay endpoints
para crear, editar ni borrar zonas, destinos, rutas o usuarios: eso solo se hace en `/admin/`.

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/zonas/` · `/api/zonas/{id}/` | Zonas (comunes a todos) |
| POST | `/api/zonas/reconocer/` | Foto (`multipart`, campo `foto`) → zona y semáforo |
| GET | `/api/destinos/` · `/api/destinos/{id}/` | Destinos. Filtros: `?tipo=`, `?q=`, `?zona=` |
| POST | `/api/rutas/calcular/` | `{"origen_id", "destino_id"}` → ruta, indicaciones y escena 3D |
| GET | `/api/historial/` · `/api/historial/{id}/` | Historial **del usuario actual** (más reciente primero) |
| POST | `/api/historial/` | Guarda la ruta actual (botón «Guardar en mi historial») |
| GET | `/api/usuarios/yo/` | Datos del usuario actual |
| GET | `/api/usuarios/carreras/` | Top 5 de carreras con más estudiantes |

- **Sin datos:** responde 404 con `{"detalle": "No hay datos disponibles."}`.
- **Ruta no registrada:** responde 404 con `{"detalle": "No encontramos una ruta disponible. …"}`.

### Semáforo de reconocimiento (`vision/utils.py`)

| Confianza | Semáforo | Mensaje |
|---|---|---|
| ≥ 0.85 | Verde | «¡Zona reconocida! Estás en: {zona}.» |
| 0.65 – 0.85 | Amarillo | «Zona detectada con confianza media. Estás en: {zona}.» |
| < 0.65 | Rojo | «No pudimos reconocer tu ubicación. Intenta con otra foto.» |

La simulación genera confianzas entre 0.65 y 0.98 (verde o amarillo). El rojo aparecerá con
el modelo YOLO real.

---

## 4. Flujo de la página única

```text
Inicio ──► ¿Dónde estoy? ──foto──► POST /api/zonas/reconocer/
                                        │
             ┌──── rojo ────────────────┼──── 404 (zona no registrada) ──► Sin datos
             ▼                          ▼ verde / amarillo
   Error de reconocimiento        Zona detectada ──► Destinos (buscador + filtros)
                                                          │ «Ver ruta»
                                                          ▼
                                        POST /api/rutas/calcular/
                                    404 ◄───┴───► 200
                                     ▼             ▼
                               Sin ruta      Ruta calculada ──► Recorrido 3D
                                                                      │ «Finalizar»
                                                                      ▼
   Historial ◄── «Repetir» ── POST /api/historial/ ◄── «Guardar» ── Llegada
```

- **Navegación:** usa el *hash* de la URL (`#inicio`, `#camara`…), así funcionan el menú y el
  botón «Atrás».
- **Sin consulta:** si se entra a «Mi ruta» o al 3D sin haber calculado una ruta, se muestra
  «Sin consulta seleccionada».

---

## 5. Cálculo de rutas (Dijkstra)

### 5.1 El campus como grafo

| Elemento | Qué es |
|---|---|
| **Nodos** | Los **pasillos** registrados en el admin (si no hay, los de `rutas/mapa_campus.py`), las zonas del admin y el destino elegido |
| **Aristas** | Las **conexiones** del admin unen los pasillos; su distancia puede indicar un rodeo real. Cada zona se conecta **sola** a sus 2 pasillos más cercanos, así que una zona nueva no requiere tocar código. El destino se conecta a su zona |
| **Peso** | Distancia real en metros (las coordenadas se pasan a metros locales) |

### 5.2 Algoritmo

`GrafoCampus.camino_mas_corto()` usa una cola de prioridad (`heapq`). Su complejidad es
O((V + E) log V).

```text
distancias[origen] = 0;  cola = [(0, origen)]
mientras haya nodos en la cola:
    tomar el de menor distancia; si ya se visitó, saltarlo
    si es el destino: terminar
    para cada vecino: si se llega más corto, actualizar distancia y "previo"
reconstruir el camino siguiendo "previo" desde el destino
```

### 5.3 Indicaciones

En cada cruce se calcula el **producto cruz** entre el tramo anterior y el siguiente:

- positivo → «gira a la derecha»;
- negativo → «gira a la izquierda»;
- casi cero (menos de ~15°) → «continúa recto».

El tiempo se estima a **1.4 m/s** (84 m/min), la velocidad peatonal estándar.

Ejemplo real con los datos de prueba (Bloque A → Lab. Computación 3, 145 m, 2 min):
1. Desde Bloque A, camina 60 m hacia el norte.
2. En Plaza Central, gira a la derecha y avanza 76 m.
3. En Bloque C, busca «Lab. Computación 3» (9 m).
4. ¡Llegaste a Lab. Computación 3!

### 5.4 ¿Cuándo se calcula?

| Momento | Qué pasa |
|---|---|
| Al guardar una ruta en el admin con distancia o camino vacíos | Se calcula al guardar |
| Al consultar una ruta cargada con `seed_data.sql` (camino `[]`) | Se calcula y se guarda la primera vez |
| Acción del admin «Recalcular distancia y camino» | Se recalcula siempre |

---

## 6. Modelo de datos

```text
┌───────────────────────┐           ┌──────────────────────┐
│ usuarios_usuario      │           │ zonas_zona           │
│ username, email       │           │ nombre (único)       │
│ es_estudiante         │           │ descripcion          │
│ carrera, semestre     │           │ latitud, longitud    │
│ is_staff (=0 alumno)  │           │ imagen_referencia    │
└──────────┬────────────┘           └──┬────────────────┬──┘
           │ 1                       1 │                │ 1
           │                     N     ▼                │
           │                ┌──────────────────────┐    │
           │                │ zonas_destino        │    │
           │                │ nombre, tipo         │    │
           │                │ latitud, longitud    │    │
           │                └──────────┬───────────┘    │
           │                         1 │                │
           │                         N ▼              N ▼
           │                ┌─────────────────────────────────┐
           │                │ rutas_ruta                      │
           │                │ origen → zona · destino → dest. │
           │                │ distancia · camino_json         │
           │ N              └──────────────┬──────────────────┘
           ▼                             1 │
┌──────────────────────────────────────────▼─┐
│ rutas_historial                            │
│ usuario · ruta · fecha · foto_origen       │
└────────────────────────────────────────────┘
```

El detalle de las tablas está en `database/init.sql`.

---

## 7. Visión artificial

```text
vision/services.py
    reconocer_zona(foto)
        ├── IA_SERVICE_URL definido ──► reconocer_zona_ia_service(foto)    [PENDIENTE]
        │                                HTTP → microservicio ia_service
        ├── modelos en ml/models/ ────► reconocer_zona_modelo_local(foto)  [LISTO]
        │                                1. YOLOv8 detecta objetos (letrero, puerta…)
        │                                2. TF-IDF + RandomForest: objetos → zona
        └── ninguno ──────────────────► reconocer_zona_simulado(foto)      [ACTUAL]
                                         «Bloque A», confianza 0.65–0.98, 5 cajas
```

### 7.1 Pipeline de entrenamiento (`backend/ml/`)

| Paso | Script | Produce |
|---|---|---|
| 1 | `entrenar_yolo.py` (o `--copiar best.pt`) | `models/yolo_zone.pt` |
| 2 | `preparar_datos_clasificador.py`: pasa YOLO por fotos clasificadas por zona | `dataset/clasificador.csv` (`image_id, objects, zone`) |
| 3 | `entrenar_clasificador.py`: TF-IDF + RandomForest (1000 árboles) | `models/zone_classifier.pkl`, `models/tfidf.pkl` y la precisión frente a la meta del 65 % |

Los modelos se cargan **una sola vez** (`lru_cache`). La primera foto tarda más y las
siguientes reutilizan los modelos en memoria. Si YOLO no detecta ningún objeto, el resultado
es semáforo **rojo**.

### 7.2 Métricas

| Métrica | Meta | Cómo se mide |
|---|---|---|
| Precisión del clasificador | ≥ 65 % | `entrenar_clasificador.py` (datos de prueba separados) |
| Reconocimiento | ≤ 5 s | La API devuelve `tiempo_ms` y se muestra en «Zona detectada» |
| Simulación 3D | ≥ 30 FPS | Contador en la vista 3D (verde si cumple, rojo si no) |

### 7.3 Formato común

El microservicio (y cualquier modo) debe devolver el mismo JSON:

```json
{"zona": "Bloque A", "confianza": 0.93,
 "detecciones": [{"clase": "Bloque A", "confianza": 0.93, "caja": [x1, y1, x2, y2]}]}
```

El nombre de cada clase de YOLO debe coincidir con el **nombre de la Zona** en el admin.

---

## 8. Seguridad

| Medida | Dónde |
|---|---|
| API solo con sesión (`IsAuthenticated`) y de solo lectura | `settings.REST_FRAMEWORK`, `ReadOnlyModelViewSet` |
| Historial filtrado por `usuario = request.user` | `rutas/views.py` |
| Token CSRF en todos los POST (cookie `csrftoken` + cabecera `X-CSRFToken`) | `web/views.py`, `api.js` |
| Logout solo por POST | Django 5 `LogoutView` |
| «Recuperar usuario» muestra siempre el mismo mensaje | `web/views.py` |
| Textos de la API insertados con `textContent`, nunca con `innerHTML` | `ruta.js`, `app.js` |
| Secretos en `.env` (fuera de git) | `settings.py` + python-dotenv |
| `ALLOWED_HOSTS="*"` y CORS abierto **solo** con `DEBUG=True` | `settings.py` |

---

## 9. Frontend

| Archivo | Responsabilidad |
|---|---|
| `index.html` | Las 10 pantallas, más «Sin datos», como `<section data-pantalla>` |
| `app.js` | Navegación, estado de la consulta y flujo completo |
| `api.js` | `fetch` a `/api` con sesión y CSRF |
| `camera.js` | Cámara en vivo (solo en HTTPS o localhost) y subida desde galería |
| `ruta.js` | Destinos (buscador y filtros), resumen, indicaciones y mapa SVG |
| `simulacion.js` | Escena 3D con Three.js: edificios, camino y cubo animado |
| `password.js` | Botón «ojo» para mostrar u ocultar la contraseña |
| CSS | `app.css` (global), `dashboard.css`, `camera.css`, `ruta.css`, `simulacion.css`, `login.css` |

**Diseño adaptable:**
- **Celular (< 900 px):** navegación abajo y una columna.
- **Laptop (≥ 900 px):** navegación arriba, dos columnas y ancho máximo de 1100 px.

**Paleta:**
- Marca `#0D47A1` · Secundario `#FF6F00` · Fondo `#F5F5F5` · Superficie `#FFFFFF`
- Texto `#212121` · Texto2 `#6E5A46` · Borde `#E6DCCB`
- Verde `#2E7D32` · Amarillo `#FF8F00` · Rojo `#C62828`

**Tipografía:** Space Grotesk en títulos e IBM Plex Sans en el cuerpo.

---

## 10. Pruebas (`python manage.py test`)

| Archivo | Qué prueba |
|---|---|
| `zonas/tests.py` | Sesión obligatoria, solo lectura, filtros, 404 «sin datos», reconocimiento y fotos inválidas |
| `rutas/tests.py` | Dijkstra (desvío más corto, sin conexión), giros, pasillos y conexiones del admin, fixture `datos_demo`, ruta inexistente, historial privado |
| `vision/tests.py` | Semáforo en los límites 0.65 y 0.85, Haversine, simulación, elección del modo local, clasificador de zonas |
| `usuarios/tests.py` | Ranking de carreras (solo estudiantes), datos del usuario sin contraseña |
| `web/tests.py` | Login, sin registro público, logout por POST, recuperación de contraseña y de usuario, admin bloqueado |
