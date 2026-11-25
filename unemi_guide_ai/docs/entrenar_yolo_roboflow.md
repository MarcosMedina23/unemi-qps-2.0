# Entrenar el reconocimiento de zonas (Roboflow + YOLO26)

El estudiante toma una foto y la app le dice **en qué zona del campus está**.
Para eso se entrena un modelo **YOLO26n** donde cada **clase es una zona**.

| Paso | Dónde | Resultado |
|---|---|---|
| 1. Etiquetar fotos | Roboflow (proyecto `unemi-zonas`) | Fotos con un recuadro y el nombre de la zona |
| 2. Entrenar | Google Colab (`backend/ml/entrenar_yolo_colab.ipynb`) | `modelo_unemi.zip` con `best.pt` y `data.yaml` |
| 3. Instalar | Servidor (`ia_service/models/best.pt`) | La cámara de la app reconoce la zona |

---

## La regla más importante: los nombres

Cada clase corresponde a **una zona de la app**. El proyecto de Roboflow
**`unemi-zonas`** (workspace *UNEMI Guide AI*) ya tiene las clases creadas y
**bloqueadas**: al etiquetar solo se elige de la lista, no se escribe. La lista está en
[`backend/ml/roboflow/clases_zonas.txt`](../backend/ml/roboflow/clases_zonas.txt).

Roboflow no acepta tildes ni paréntesis, así que tres clases se escriben distinto;
la app las une sola con la zona correcta (ignora tildes, signos y mayúsculas):

| Clase en Roboflow | Zona en la app |
|---|---|
| `Bloque T -FACI-` | Bloque T (FACI) |
| `Bloque de Investigacion de Biotecnologia` | Bloque de Investigación de Biotecnología |
| `Entrada de vehiculos` | Entrada de vehículos |

Son **30 clases**:

| Bloques | Edificios | Deportes, accesos y exteriores |
|---|---|---|
| Bloque B · Bloque C · Bloque E · Bloque F | CRAI | Estadio Universitario UNEMI |
| Bloque H · Bloque I · Bloque J | Posgrado | Piscina UNEMI |
| Bloque K · Bloque L · Bloque M · Bloque N | SIM | Entrada de vehiculos |
| Bloque O · Bloque P · Bloque R | CDIP | Area verde -Bloques R-U- · Area verde sur |
| Bloque S · Bloque T -FACI- · Bloque U | Bloque de Investigacion de Biotecnologia | Estacionamiento 1 · Estacionamiento 2 |
| Bloques V-W-X | | |

No se usan los baños ni los edificios anexos: se parecen entre sí y confunden al modelo.
En áreas verdes y estacionamientos usa fotos donde se vea algo que los distinga
(bancas, letreros o un bloque al fondo).

### Grupos: varios lugares, una sola clase

Algunos lugares están tan juntos que en una foto casi siempre salen a la vez. Si fueran
clases separadas, el modelo los confundiría. Por eso se etiquetan con **una sola clase**
y la app muestra qué lugares incluye esa zona (archivo `backend/zonas/grupos_ia.py`).
El mapa del GPS y las rutas **no cambian**: cada lugar sigue siendo un destino propio.

| Clase en Roboflow | La app ubica al estudiante en | La zona incluye |
|---|---|---|
| `Bloques V-W-X` | Bloque W | Bloque V, Bloque W, Bloque X |
| `Bloque H` | Bloque H | Bloque H, bar del Bloque H, Entrada peatonal |
| `Estadio Universitario UNEMI` | Estadio Universitario UNEMI | Estadio, polideportivo, bar del polideportivo, Canchas |
| `Piscina UNEMI` | Piscina UNEMI | Piscina, gimnasio, Monumento de las Banderas |

**Regla de subida** (en qué clase va cada foto):

- Fotos del **Bloque V, W o X** → `Bloques V-W-X`.
- Fotos del **bar del Bloque H** o de la **Entrada peatonal** → `Bloque H`.
- Fotos de las **canchas**, el **polideportivo** o **su bar** → `Estadio Universitario UNEMI`.
- Fotos del **gimnasio** o del **Monumento de las Banderas** → `Piscina UNEMI`.

Ya **no existen** las clases `Bloque V`, `Bloque W`, `Bloque X`, `Canchas`,
`Entrada peatonal` ni `Monumento de las Banderas`: si Roboflow todavía las tiene,
reasigna sus fotos según la regla de arriba y bórralas antes de generar la versión.

**Cerca (solo información):** cuando el modelo detecta `Bloque N`, la app avisa que
cerca hay un **baño** y un **bar**. No son clases ni lugares del mapa (no tenemos su
ubicación exacta).

### ¿Cuántas fotos?

- Mínimo **40 fotos por zona**; lo ideal, 80 o más.
- Con unas 300 fotos, empieza con **5 a 8 zonas** bien fotografiadas. Después se agregan
  más zonas y se vuelve a entrenar.
- Mezcla: de cerca y de lejos, distintos ángulos, mañana y tarde, con gente pasando.
  Así se parecerán a la foto que toma un estudiante con su celular.

---

## Paso 1 · Roboflow: etiquetar las fotos

1. Entra a <https://app.roboflow.com> → workspace **UNEMI Guide AI** → proyecto **`unemi-zonas`** (Object Detection, privado).
2. **Upload Data** → arrastra las fotos → **Save and Continue**.
3. **Annotate** → abre cada foto:
   - Dibuja un **rectángulo** que cubra la fachada o el letrero de la zona.
   - Elige la clase de la lista (no escribas una nueva).
   - Un solo rectángulo por foto basta; si salen dos zonas claras, marca las dos.
4. Cuando termines un lote: **Add images to Dataset** → reparto **70 % train / 20 % valid / 10 % test**.
5. **Versions → Generate New Version**:
   - *Preprocessing*: Auto-Orient y Resize a 640×640 (Stretch).
   - *Augmentations*: Brightness (±20 %), Rotation (±10°), Blur leve.
   - **Create**.
6. En la versión creada: **Download Dataset** → formato **YOLO26** → **Show download code**
   → copia el código de *Jupyter*. Lo pegarás en Colab.

---

## Paso 2 · Google Colab: entrenar

1. Abre <https://colab.research.google.com> → **Subir** → elige
   `backend/ml/entrenar_yolo_colab.ipynb` (o ábrelo desde GitHub).
2. **Entorno de ejecución → Cambiar tipo → GPU (T4)**.
3. Ejecuta las celdas en orden:
   1. Instala `ultralytics` y `roboflow`.
   2. Pega el código de Roboflow (descarga las fotos).
   3. **Revisa los nombres**: todos deben salir con ✅.
   4. Entrena YOLO26n (20–60 min).
   5. Muestra el **mAP50** y la matriz de confusión.
   6. Prueba con fotos que el modelo nunca vio.
   7. Descarga **`modelo_unemi.zip`**.

| mAP50 | Significado |
|---|---|
| > 0.8 | Bueno |
| 0.6 – 0.8 | Aceptable para una demo |
| < 0.6 | Faltan fotos o hay recuadros mal puestos |

---

## Paso 3 · Instalar en la app

Envía a quien administra el servidor:

- `modelo_unemi.zip` (`best.pt` + `data.yaml` + gráficas).
- 3 a 5 fotos del campus que **no** se subieron a Roboflow, para probar.

En el servidor el modelo va en `ia_service/models/best.pt` y se activa con
`IA_SERVICE_URL` en `backend/.env`. Si el servidor no tiene memoria suficiente para
PyTorch, se sube el plan de Lightsail a 2 GB. Mientras no haya modelo, la app sigue
funcionando en **modo simulado**.

> `*.pt` está en `.gitignore`: el modelo **no** se sube a GitHub.
