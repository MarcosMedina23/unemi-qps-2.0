# UNEMI Guide AI — reglas para cambios

Backend Django en `backend/` (pruebas: `cd backend && python manage.py test`).

## Reconocimiento por foto (YOLO + Roboflow)

- **Las clases de Roboflow no llevan tildes ni paréntesis** (`Bloque T -FACI-`,
  `Entrada de vehiculos`). La app las une con la zona real mediante
  `clave_nombre()` en `backend/zonas/views.py` (ignora tildes, signos, espacios y
  mayúsculas). Toda comparación de nombres de clase debe usar `clave_nombre()`.
- La lista oficial de clases está en `backend/ml/roboflow/clases_zonas.txt` y debe ser
  **idéntica** a `CLASES_DE_LA_APP` en `backend/ml/entrenar_yolo_colab.ipynb`
  (hoy son 29). Si cambias una, cambia la otra y `docs/entrenar_yolo_roboflow.md`.
- `Area verde sur` **no** es clase de la IA (lote vacío), pero **sigue** como zona/destino
  del mapa del GPS. No borrarla.
- Fotos que no son ninguna zona se suben a Roboflow como **Null** (sin recuadro). Si el
  modelo devuelve una clase de `CLASES_SIN_ZONA` ("Nada"...), la app responde
  "no reconocida" (400, semáforo rojo).
- El entrenamiento usa `fliplr=0.0` (sin espejo: los letreros deben leerse bien).

### Grupos (`backend/zonas/grupos_ia.py`)

- `GRUPOS_IA`: una clase de la IA que abarca varios lugares cercanos.
  `buscar_zona()` devuelve su **zona principal** y `/api/zonas/reconocer/` añade
  `"grupo": {"clase", "incluye", "cerca"}`.
  - `Bloques V-W-X` → Bloque W (incluye Bloque V, W, X)
  - `Bloque H` → Bloque H (incluye su bar y la Entrada peatonal)
  - `Estadio Universitario UNEMI` → Estadio (incluye polideportivo, su bar y Canchas)
  - `Piscina UNEMI` → Piscina (incluye gimnasio y Monumento de las Banderas)
- `CERCA_DE`: lugares cercanos **solo informativos** (`Bloque N`: Baño, Bar). No son
  clases ni lugares del mapa: no se crean zonas ni destinos para ellos.
- Los nombres de clase viejos (`Bloque V`, `Canchas`, `Entrada peatonal`, ...) deben
  seguir resolviendo cada uno a su propia zona (modelos entrenados antes).
- En `/api/zonas/reconocer/` no se quitan ni renombran campos existentes
  (`zona`, `confianza`, `semaforo`, `mensaje`, `detecciones`, `modo`, `simulado`,
  `tiempo_ms`, `grupo`): la web y Unity dependen de ellos.

## Mapa del GPS y rutas

- Los grupos de la IA **no** cambian el mapa. **No borrar zonas ni destinos del GPS**
  (base de datos ni `campus_unemi.json`): cada lugar sigue siendo un destino propio.
- `unity/herramientas/campus_data.py`, `gen_web.py`, `CampusData.cs` y
  `backend/web/static/web/data/campus_unemi.json` son la fuente del mapa; solo se tocan
  cuando el cambio es del mapa en sí.

## Nunca subir

- `backend/.env`, `backend/db.sqlite3`, modelos `*.pt`.
