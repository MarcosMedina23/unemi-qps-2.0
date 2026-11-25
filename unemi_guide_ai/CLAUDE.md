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

### Respuesta "inteligente" (`backend/zonas/reconocimiento.py`, `backend/vision/calidad.py`)

- Siempre se busca dar la respuesta más acertada; nunca un simple "no sé" si hay pistas.
- Se juntan tres pistas: IA (todas las detecciones), calidad de la foto (Pillow:
  movida, oscura, quemada, tapada, pequeña) y GPS del celular (opcional).
- El GPS solo se manda si la foto viene de la **cámara** (no de la galería).
- `motivo` en la respuesta 400: `dudosa` (con `opciones` para elegir), `foto_mala`
  (consejos + opciones), `fuera_del_campus`, `sin_deteccion`. `detalle` conserva el
  mensaje de siempre para `sin_deteccion` y `foto_mala`.
- Foto mala solo se rechaza si la IA no está muy segura (< 0.85). Mensaje: borrosa →
  "vuelve a tomarla con el celular quieto"; oscura/quemada/tapada → "con buena luz".
- Confianza media (0.35 a 0.65, sin empate): 200 amarillo "Estás cerca del Bloque X,
  junto al Bloque Y" con `"aproximada": true` y `"junto_a"` (zona más cercana).
- `IA_PERMITIR_SIMULACION=False` (servidor con modelo real): si la IA falla no se inventa
  zona; 400 rojo con `motivo: "ia_no_disponible"`.
- ia_service usa `models/best.onnx` + `data.yaml` con onnxruntime (sin PyTorch,
  `requirements-ligero.txt`); si no hay `.onnx`, usa `best.pt`. Pruebas:
  `cd ia_service && ..\venv\Scripts\python -m unittest test_modelo_onnx`.
- Los umbrales de calidad se calibraron con fotos reales a 512 px; si se cambian,
  probar con `foto_jpeg("borrosa"/"oscura")` de `zonas/tests.py`.

## Mapa del GPS y rutas

- Los grupos de la IA **no** cambian el mapa. **No borrar zonas ni destinos del GPS**
  (base de datos ni `campus_unemi.json`): cada lugar sigue siendo un destino propio.
- `unity/herramientas/campus_data.py`, `gen_web.py`, `CampusData.cs` y
  `backend/web/static/web/data/campus_unemi.json` son la fuente del mapa; solo se tocan
  cuando el cambio es del mapa en sí.

## Nunca subir

- `backend/.env`, `backend/db.sqlite3`, modelos `*.pt` y `*.onnx`.
