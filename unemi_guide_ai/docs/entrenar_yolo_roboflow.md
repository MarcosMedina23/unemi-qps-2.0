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

Cada clase debe llamarse **exactamente igual** que la zona en la app: mayúsculas,
tildes, espacios y paréntesis. `Bloque T (FACI)` funciona; `bloque t` o `Bloque T`
no. La lista oficial está en [`backend/ml/roboflow/clases_zonas.txt`](../backend/ml/roboflow/clases_zonas.txt)
y el proyecto de Roboflow ya trae esas clases creadas.

| Bloques | Edificios | Deportes y accesos |
|---|---|---|
| Bloque B · Bloque C · Bloque E | CRAI | Estadio Universitario UNEMI |
| Bloque H · Bloque I · Bloque J | Posgrado | Piscina UNEMI |
| Bloque K · Bloque M · Bloque N | SIM | Canchas |
| Bloque O · Bloque P · Bloque R | CDIP | Monumento de las Banderas |
| Bloque S · Bloque T (FACI) · Bloque U | Bloque de Investigación de Biotecnología | Entrada peatonal |
| Bloque V · Bloque W · Bloque X | | Entrada de vehículos |

No se usan los baños, los edificios anexos, los estacionamientos ni las áreas verdes:
se parecen entre sí y confunden al modelo.

### ¿Cuántas fotos?

- Mínimo **40 fotos por zona**; lo ideal, 80 o más.
- Con unas 300 fotos, empieza con **5 a 8 zonas** bien fotografiadas. Después se agregan
  más zonas y se vuelve a entrenar.
- Mezcla: de cerca y de lejos, distintos ángulos, mañana y tarde, con gente pasando.
  Así se parecerán a la foto que toma un estudiante con su celular.

---

## Paso 1 · Roboflow: etiquetar las fotos

1. Entra a <https://app.roboflow.com> y abre el proyecto **`unemi-zonas`** (Object Detection).
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
