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
| Rutas | Algoritmo de Dijkstra propio sobre el grafo de pasillos |
| Frontend | HTML + CSS + JavaScript puro, servido por Django |
| 3D | Three.js (CDN) |
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
├── database/
│   ├── init.sql              Esquema de las tablas (referencia)
│   └── seed_data.sql         Datos de prueba en SQL (referencia; usa loaddata)
├── scripts/
│   └── compartir_enlace.ps1  Crea el enlace público https (lo usa compartir_enlace.bat)
├── compartir_enlace.bat      Doble clic: comparte la app con un enlace público
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

## Compartir el enlace con otra persona

### Opción A · Enlace público con Cloudflare (recomendada)

Crea un enlace `https://…trycloudflare.com` que apunta a tu PC. Cualquiera con el enlace
puede entrar desde su celular o computadora, aunque esté en otra red, y la cámara en vivo
funciona porque es `https`. `settings.py` ya acepta estos enlaces (`CSRF_TRUSTED_ORIGINS`).

**La forma fácil: doble clic en `compartir_enlace.bat`** (carpeta raíz del proyecto).

El script hace todo solo:
1. Instala `cloudflared` la primera vez. Windows puede pedirte permiso.
2. Enciende el servidor, o usa el que ya esté encendido.
3. Muestra el enlace en grande y lo **copia al portapapeles**. Solo pégalo con `Ctrl + V`
   en WhatsApp o correo.
4. Al presionar **Enter** en esa ventana, cierra el enlace.

La lógica está en `scripts/compartir_enlace.ps1`.

**La forma manual** (lo mismo, paso a paso):

**Paso 1 · Instalar cloudflared** (solo la primera vez):
```powershell
winget install --id Cloudflare.cloudflared
```
Al terminar, **cierra PowerShell y ábrelo de nuevo** para que reconozca el comando.

**Paso 2 · Terminal 1: arrancar el servidor**
```powershell
cd "C:\Users\USER\Downloads\GPS UNEMI\unemi_guide_ai"
venv\Scripts\activate
cd backend
python manage.py runserver
```

**Paso 3 · Terminal 2 (otra ventana): abrir el túnel**
```powershell
cloudflared tunnel --url http://localhost:8000
```
A los pocos segundos aparece un enlace como `https://palabras-al-azar-1234.trycloudflare.com`.
**Ese es el link que compartes.**

**Paso 4 · Crear la cuenta de la otra persona**

No hay registro público, así que sin una cuenta no podrá pasar del login:
1. Entra a `/admin/` → **Usuarios → Añadir usuario** y crea su cuenta **sin** «Staff status».
2. Envíale el link, su usuario y su contraseña.

**Ten en cuenta:**
- Tu PC debe seguir **encendida** y con las **dos terminales abiertas**. Si cierras una, el
  link deja de funcionar.
- El link **cambia cada vez** que vuelves a ejecutar `cloudflared`: envía el nuevo.
- Mientras el túnel esté abierto, tu PC es accesible desde internet. Usa una contraseña fuerte
  en el superusuario y cierra el túnel con `Ctrl + C` al terminar la demostración.

### Opción B · Misma red Wi-Fi (sin instalar nada)

```powershell
python manage.py runserver 0.0.0.0:8000
```
1. Busca tu IP con `ipconfig` (línea «Dirección IPv4», por ejemplo `192.168.1.25`).
2. Comparte `http://192.168.1.25:8000`.

- Si Windows pregunta por el firewall, permite el acceso en **redes privadas**.
- Por `http` la cámara en vivo no funciona: hay que usar «Subir desde galería», que en el
  celular también deja tomar la foto.

---

## Pruebas automáticas

```powershell
python manage.py test
```

Son 42 pruebas. Cubren:
- **API:** acceso solo con sesión, solo lectura, filtros, 404, semáforo (incluido el rojo) y
  tiempo de reconocimiento ≤ 5 s.
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

- **Microservicio `ia_service`:** si YOLO debe correr en otro servidor, se define
  `IA_SERVICE_URL` en `.env` y se completa `reconocer_zona_ia_service()` en
  `vision/services.py`.
- **Servidor en la nube** con enlace fijo, HTTPS y PostgreSQL. También hay que decidir dónde
  corre YOLO.
- **AWS S3** con django-storages: el bloque de configuración ya está comentado en `settings.py`.
- **Seguridad antes de entregar:**
  - cambiar la contraseña de aplicación de Gmail si estuvo expuesta;
  - poner `DJANGO_DEBUG=False`, que también cierra `ALLOWED_HOSTS` y CORS;
  - usar una `DJANGO_SECRET_KEY` nueva y una contraseña fuerte para el superusuario.

---

## Documentación

- [docs/arquitectura.md](docs/arquitectura.md): cómo está construido.
- [docs/manual_usuario.md](docs/manual_usuario.md): cómo se usa.
