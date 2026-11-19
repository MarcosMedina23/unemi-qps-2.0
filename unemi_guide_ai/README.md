# UNEMI Guide AI

> Toma una foto, descubre dónde estás y llega a tu destino por el camino más corto.

Sistema de orientación dentro del campus de la **Universidad Estatal de Milagro (UNEMI)**
para estudiantes de nuevo ingreso. El estudiante toma una foto de su entorno, el sistema
reconoce la zona con visión artificial (**simulada** hasta que entrenes el modelo), calcula
la ruta más corta hasta el destino y la muestra en un mapa y en **3D**.

Proyecto académico · Construcción de Software.

---

## Reglas de negocio

- **No hay registro público.** El administrador crea las cuentas de los estudiantes en `/admin/`.
- El **estudiante** solo consulta: no puede crear ni modificar nada.
- El **administrador** gestiona zonas, destinos, rutas y usuarios desde `/admin/`.

---

## Tecnologías

| Parte | Tecnología |
|---|---|
| Backend y API | Django 5.2 + Django REST Framework |
| Base de datos | SQLite (desarrollo) |
| Imágenes | Pillow |
| Visión artificial (opcional) | YOLOv8 (Ultralytics) + TF-IDF + RandomForest (scikit-learn) |
| Microservicio de IA | FastAPI + YOLOv8 (`ia_service/`, puerto 8001) |
| Rutas | Dijkstra con NetworkX sobre el grafo de pasillos |
| Frontend | HTML + CSS + JavaScript puro, servido por Django |
| 3D | Three.js en la web · Unity: campus UNEMI real con personita que camina (`unity/`) |
| Configuración | python-dotenv (`backend/.env`) |
| Otros | django-cors-headers, boto3 (S3, pendiente) |

---

## Métricas objetivo

| Métrica | Meta | Dónde se ve |
|---|---|---|
| Precisión del modelo de zonas | ≥ 65 % | Lo imprime `ml/entrenar_clasificador.py` |
| Tiempo de reconocimiento | ≤ 5 s | Pantalla «Zona detectada» («Analizada en … s») y campo `tiempo_ms` de la API |
| Fluidez de la simulación 3D | ≥ 30 FPS | Contador verde/rojo en la esquina de la vista 3D |

---

## Estructura del proyecto

Todo vive en **una sola carpeta**, `unemi_guide_ai/`:

```text
unemi_guide_ai/
├── venv/                     Entorno virtual de Python (no se sube a git)
├── backend/                  Proyecto Django
│   ├── manage.py
│   ├── requirements.txt      Dependencias exactas (pip freeze)
│   ├── .env / .env.example   Variables de entorno (secretos)
│   ├── config/               settings.py, urls.py, wsgi.py, asgi.py
│   ├── usuarios/             Modelo Usuario, admin, ranking de carreras
│   ├── zonas/                Zona y Destino, API y reconocimiento por foto
│   ├── rutas/                Pasillo, Conexion, Ruta, Historial, API y Dijkstra
│   │   └── fixtures/         datos_demo.json (datos de prueba para loaddata)
│   ├── vision/               Reconocimiento (simulado / modelo local / ia_service), semáforo
│   ├── ml/                   Entrenamiento: YOLOv8 + clasificador TF-IDF/RandomForest
│   │   ├── entrenar_yolo.py · preparar_datos_clasificador.py · entrenar_clasificador.py
│   │   ├── dataset/dataset.yaml · requirements-ml.txt
│   │   └── models/           Aquí quedan yolo_zone.pt, zone_classifier.pkl, tfidf.pkl
│   └── web/                  Página única, login y recuperación de cuenta
│       ├── forms.py · views.py · urls.py
│       ├── static/web/       css/ · js/ · img/logo.png
│       └── templates/        web/index.html · registration/login.html · recuperar/
├── ia_service/               Microservicio de IA (FastAPI + YOLOv8)
│   ├── main.py               POST /predict y GET /health
│   ├── requirements.txt
│   └── models/               Aquí va tu best.pt
├── unity/                    Campus UNEMI en 3D (Unity, C#) — ver unity/LEEME.md
│   ├── Assets/UNEMI/Editor/  UNEMICampusBuilder.cs (menú UNEMI > Generar Campus 3D)
│   ├── Assets/UNEMI/Scripts/ CampusData · RutaCampus · PersonaCaminante · GrafoCalles
│   │                         CampusCameraController · CampusLocation · ApiClient ...
│   └── herramientas/         campus_data.py + gen_cs.py (regeneran CampusData.cs)
├── database/
│   ├── init.sql              Esquema de las tablas (referencia)
│   └── seed_data.sql         Datos de prueba en SQL (referencia; usa loaddata)
├── docs/
│   ├── README.md             Índice y glosario
│   ├── arquitectura.md       Arquitectura, API, algoritmo y modelo de datos
│   └── manual_usuario.md     Manual para el estudiante y el administrador
└── README.md                 Este archivo
```

---

## Instalación (Windows · PowerShell)

Ejecuta los comandos **uno por uno**.

```powershell
# 1. Entrar al proyecto y activar el entorno virtual
cd "C:\Users\USER\Downloads\GPS UNEMI\unemi_guide_ai"
venv\Scripts\activate

# 2. Entrar al backend
cd backend

# 3. (Solo si el venv es nuevo) instalar dependencias
pip install -r requirements.txt

# 4. Crear las tablas
python manage.py migrate

# 5. Crear tu cuenta de administrador (te pedirá usuario, correo y contraseña)
python manage.py createsuperuser

# 6. (Opcional) cargar datos de prueba: 5 zonas, 6 destinos, 3 pasillos y 4 rutas
python manage.py loaddata datos_demo

# 6b. Cargar el campus UNEMI real (el mismo del modelo 3D de Unity):
#     bloques, edificios, baños, canchas, estacionamientos, áreas verdes,
#     entrada y salida + las calles como pasillos + todas las rutas.
#     Reemplaza los pasillos de prueba. Se puede repetir sin duplicar nada.
python manage.py cargar_campus

# 7. Arrancar el servidor
python manage.py runserver
```

- Web del estudiante: **http://127.0.0.1:8000**
- Administración: **http://127.0.0.1:8000/admin/**

> Si PowerShell no deja activar el venv, ejecuta una vez:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### Primeros pasos en el admin

1. **Usuarios → Añadir:** crea al estudiante **sin** marcar «Staff status».
2. **Zonas:** crea las zonas. La simulación siempre reconoce **«Bloque A»**, así que esa debe existir.
3. **Destinos:** crea los destinos de cada zona.
4. **Pasillos del campus** (opcional): registra los cruces por donde se camina y únelos en
   «Conexiones». Cada zona se conecta sola a sus 2 pasillos más cercanos. Si no registras
   ninguno, se usan los de `rutas/mapa_campus.py`.
5. **Rutas:** elige origen y destino y deja la distancia y el camino **vacíos**: se calculan solos.

---

## Correo real para recuperar contraseña (mmedinal2@unemi.edu.ec)

La recuperación de contraseña (`/recuperar/`) y de usuario (`/recuperar-usuario/`) ya
funciona. Los correos salen desde **mmedinal2@unemi.edu.ec**, que ya está configurado en
`backend/.env`. Solo falta la **contraseña de aplicación**.

### Paso 1 · ¿La cuenta es de Google o de Microsoft?

Entra al correo institucional en el navegador:
- Si se abre en **mail.google.com** (Gmail), la cuenta es de Google. Sigue el paso 2.
- Si se abre en **outlook.office.com**, la cuenta es de Microsoft. En `.env` cambia a
  `EMAIL_HOST=smtp.office365.com` y crea la contraseña de aplicación desde
  **mysignins.microsoft.com → Información de seguridad**.

### Paso 2 · Crear la contraseña de aplicación (Google)

1. Inicia sesión con **mmedinal2@unemi.edu.ec** en **https://myaccount.google.com**.
2. Ve a **Seguridad** y activa **Verificación en 2 pasos**. Es obligatoria.
3. Entra a **https://myaccount.google.com/apppasswords**.
4. Escribe un nombre, por ejemplo `UNEMI Guide AI`, y pulsa **Crear**.
5. Copia las **16 letras** que aparecen. Solo se muestran una vez.
6. Pégalas en `backend/.env` y reinicia el servidor:
   ```
   EMAIL_HOST_PASSWORD=abcdefghijklmnop
   ```

Si en el paso 3 aparece «La opción que buscas no está disponible», el departamento de TI de
la UNEMI tiene desactivadas las contraseñas de aplicación para cuentas institucionales. En
ese caso pídeles que la habiliten, o usa temporalmente un Gmail personal cambiando
`EMAIL_HOST_USER` y `DEFAULT_FROM_EMAIL`.

**Probar el envío** (desde `backend`, con el venv activo):
```powershell
python manage.py sendtestemail tu_correo@unemi.edu.ec
```
Mientras `EMAIL_HOST_PASSWORD` esté vacío, el correo se muestra en la consola en vez de
enviarse.

---

## Microservicio de IA (`ia_service/`)

Servicio aparte (FastAPI) que procesa la foto con tu modelo YOLOv8 `best.pt`. Django le
envía la foto. **Si el microservicio está apagado o falla, Django usa la simulación** y la
app sigue funcionando: la pantalla muestra un aviso.

**Instalación** (en una **terminal nueva** de PowerShell):
```powershell
cd "C:\Users\USER\Downloads\GPS UNEMI\unemi_guide_ai"
venv\Scripts\activate
cd ia_service
pip install -r requirements.txt
```
Las dependencias pesan unos 2 GB por PyTorch y se instalan una sola vez. Después:
1. Copia tu `best.pt` en `ia_service\models\best.pt`.
2. Arranca el servicio:
   ```powershell
   uvicorn main:app --host 127.0.0.1 --port 8001
   ```
3. Comprueba en el navegador http://127.0.0.1:8001/health. Debe decir
   `"modelo_disponible": true`.

**Conectarlo con Django:** en `backend/.env` pon la línea de abajo y reinicia `runserver`:
```
IA_SERVICE_URL=http://127.0.0.1:8001/predict
```

¿Cómo decide Django la zona? Si `best.pt` se entrenó con las zonas como clases («Bloque A»,
«Biblioteca Central»…), usa la detección de mayor confianza. Si se entrenó con objetos
(letrero, puerta…) y existe el clasificador de `backend/ml/models/`, decide con TF-IDF +
RandomForest. **Los nombres de las clases deben ser iguales a los nombres de las zonas del
admin.**

---

## Campus 3D en Unity

La web ya muestra el recorrido en 3D con Three.js. En `unity/` está el **campus real de la
UNEMI en 3D** (bloques, baños, canchas, estadio, parqueos, calles y estero) con una
**personita que camina por las calles** hasta el destino. Guía completa: `unity/LEEME.md`.

1. Abre **Unity Hub → Add → Add project from disk** y elige la carpeta `unity`
   (o crea un proyecto 3D nuevo y copia `unity/Assets/UNEMI` dentro de su `Assets`).
2. Menú **UNEMI → Generar Campus 3D**. Crea el campus, la personita, la línea de la ruta,
   la cámara y guarda la escena en `Assets/UNEMI/Escenas/CampusUNEMI.unity`.
3. Dale **Play**: la personita camina de la entrada peatonal al aula K-301 (demo).
4. Cómo llegan los datos de Django:
   - **Unity WebGL dentro de la web:** `simulacion.js` envía la escena con
     `unityInstance.SendMessage("RouteAnimator", "LoadWaypoints", json)`. Unity busca el
     destino por nombre (`escena.destino`, p. ej. «Aula K-301» o «Bloque K») y camina por
     las calles con Dijkstra. Pausar y Repetir también se envían.
   - **Unity de escritorio:** `ApiClient.CalculateRoute(origenId, destinoId, ...)` y después
     `RutaCampus.LoadRoute(...)` (cookies `sessionid` y `csrftoken` en el Inspector).

Los nombres de zonas/destinos del admin deben parecerse a los del campus 3D («Bloque K»,
«CDIP», «CRAI»…). Si no coinciden, agrega un alias en `RutaCampus` (Inspector).

---

## Probar desde el celular

### Misma red Wi-Fi (desarrollo)

```powershell
python manage.py runserver 0.0.0.0:8000
```
1. Busca tu IP con `ipconfig` (línea «Dirección IPv4», por ejemplo `192.168.1.25`).
2. Abre `http://192.168.1.25:8000` en el celular.

- Si Windows pregunta por el firewall, permite el acceso en **redes privadas**.
- Por `http` el navegador **bloquea la cámara en vivo y el GPS**: la foto se toma con
  «Subir desde galería» y el recorrido funciona en modo **Referencial**. El modo
  **A tiempo real** necesita `https`.

### Servidor en internet (AWS · pendiente)

La app se publicará en AWS con un dominio fijo y **HTTPS**, encendida todo el tiempo. Con
HTTPS funcionan la cámara en vivo y el GPS del modo **A tiempo real**. Al desplegar:

- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS=tu-dominio.com`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://tu-dominio.com`
- `python manage.py collectstatic` y un servidor de producción (por ejemplo Gunicorn + Nginx).

---

## Pruebas automáticas

```powershell
python manage.py test
```

Son 54 pruebas. Cubren:
- **API:** acceso solo con sesión, solo lectura, filtros, 404, semáforo rojo con error 400 y
  tiempo de reconocimiento ≤ 5 s.
- **Microservicio de IA:** zona según la detección, sin detecciones, y caída automática a la
  simulación si el servicio está apagado o responde con error.
- **Rutas:** algoritmo de Dijkstra, pasillos del admin, fixture `datos_demo`, ruta inexistente,
  historial privado y que no se puede editar.
- **Visión:** elección automática del modo (simulado o local) y clasificador de zonas.
- **Login y recuperación:** registro público inexistente, logout por POST y recuperación de
  contraseña y de usuario.

---

## Visión artificial real (cuando tengas fotos o tu `best.pt`)

El reconocimiento tiene tres modos y **los elige solo** (`vision/services.py`):

| Modo | Se activa cuando… |
|---|---|
| Microservicio `ia_service` | Defines `IA_SERVICE_URL` en `.env` (pendiente) |
| **Modelo local** | Existen los 3 archivos de `ml/models/` y están instaladas las librerías de ML |
| Simulado | En cualquier otro caso (estado actual) |

El modelo local funciona en dos pasos: **YOLOv8** detecta objetos en la foto (letreros,
puertas, escaleras…) y un **clasificador TF-IDF + RandomForest** decide la zona a partir de
esos objetos.

Para pasar al **modelo local**, ejecuta estos comandos desde `backend`, con el venv activo:

```powershell
# 1. Instalar las librerías de ML (pesan ~2 GB, solo una vez)
pip install -r ml/requirements-ml.txt

# 2a. Si ya tienes tu best.pt entrenado, instálalo:
python ml/entrenar_yolo.py --copiar "C:\Users\USER\Downloads\best.pt"
# 2b. O entrena YOLO con tus fotos etiquetadas (ver ml/dataset/dataset.yaml):
python ml/entrenar_yolo.py

# 3. Pon fotos clasificadas por zona en ml/dataset/zonas/<Nombre de la zona>/ y genera el CSV
python ml/preparar_datos_clasificador.py

# 4. Entrena el clasificador (muestra la precisión frente a la meta del 65 %)
python ml/entrenar_clasificador.py
```

Al reiniciar el servidor, la app usa el modelo real: la nota «Detecciones simuladas»
desaparece sola y el semáforo rojo aparece cuando no se reconoce la zona. Los nombres de las
carpetas de `ml/dataset/zonas/` deben ser **iguales** a los nombres de las zonas del admin.

---

## Pendiente (punto de enlace listo)

- **Probar `ia_service` con el `best.pt` real.** El servicio y la integración se probaron con
  un YOLO falso, porque PyTorch no está instalado aquí.
- **Unity:** calibrar el GPS del campus (`CampusGeoReference`) y publicar el build WebGL en la web.
- **Servidor en AWS** con dominio fijo, HTTPS y PostgreSQL (ver «Servidor en internet»).
  También hay que decidir dónde corre YOLO.
- **AWS S3** con django-storages: el bloque de configuración ya está comentado en `settings.py`.
- **Seguridad antes de entregar:**
  - cambiar la contraseña de aplicación de Gmail si estuvo expuesta;
  - poner `DJANGO_DEBUG=False`, que también cierra `ALLOWED_HOSTS` y CORS;
  - usar una `DJANGO_SECRET_KEY` nueva y una contraseña fuerte para el superusuario.

---

## Documentación

- [docs/arquitectura.md](docs/arquitectura.md): cómo está construido.
- [docs/manual_usuario.md](docs/manual_usuario.md): cómo se usa.
