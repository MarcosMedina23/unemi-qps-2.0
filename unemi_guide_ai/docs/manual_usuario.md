# Manual de usuario · UNEMI Guide AI

Este manual tiene dos partes:
- **Parte A** para el **estudiante**, que usa la app para orientarse en el campus.
- **Parte B** para el **administrador**, que carga los datos.

> **Versión de demostración:** el reconocimiento por foto es simulado y siempre detecta el
> **Bloque A**. El cálculo de rutas sí es real.

---

# Parte A · Estudiante

## 1. Ingresar

1. Abre el enlace de la app que te dieron (por ejemplo, `https://….trycloudflare.com`).
2. Escribe el **usuario** y la **contraseña** que te entregó la universidad.
3. Pulsa el ícono del ojo 👁 si quieres ver la contraseña mientras la escribes.
4. Pulsa **Ingresar**.

No hay opción «Crear cuenta»: las cuentas las crea la administración de tu facultad.

**¿Olvidaste algo?**

| Problema | Qué hacer |
|---|---|
| No recuerdo mi contraseña | Pulsa **¿Olvidaste tu contraseña?**, escribe tu correo y abre el enlace que te llega. El enlace vence en 1 hora |
| No recuerdo mi usuario | Pulsa **¿Olvidaste tu usuario?** y escribe tu correo. Te llegará tu nombre de usuario |

## 2. El menú

| En el celular | En la computadora |
|---|---|
| Menú en la parte **inferior** de la pantalla | Menú en la barra **superior** |

**Opciones del menú:**
- **Inicio** · **¿Dónde estoy?** · **Destinos** · **Mi ruta** · **Historial**

Arriba a la derecha verás tu nombre y el botón **Salir**.

## 3. Inicio

Verás un saludo y dos botones: **¿Dónde estoy?** y **Ver mi historial**.

Al lado está el apartado **«Carreras que más usan la app»**, con las 5 carreras con más
estudiantes.

## 4. ¿Dónde estoy? (tomar o subir la foto)

1. Apunta a un **letrero o fachada** y pulsa **Tomar foto**.
2. O pulsa **Subir desde galería** para elegir una foto o tomarla con la cámara del celular.

| Lo que ves | Qué significa |
|---|---|
| «La cámara en vivo necesita una conexión segura» | La app se abrió por `http`. Usa **Subir desde galería** |
| «No pudimos acceder a la cámara» | Revisa que el navegador tenga permiso para usar la cámara |

## 5. Zona detectada

Verás tu foto, la zona donde estás (por ejemplo, *Bloque A — Facultad de Ciencias e
Ingeniería*) y la confianza del reconocimiento.

| Color | Significado |
|---|---|
| 🟢 Verde | Reconocida con alta confianza |
| 🟡 Amarillo | Reconocida con confianza media |
| 🔴 Rojo | No se reconoció: aparece la pantalla «No pudimos reconocer tu ubicación» con el botón **Tomar otra foto** |

Debajo verás cuánto tardó el análisis (por ejemplo, «Analizada en 0.85 s»).

Pulsa **Elegir mi destino**.

## 6. Elegir destino

- Escribe en el **buscador**. Puedes escribir sin tildes: «computacion» encuentra
  «Computación».
- Usa los filtros: **Todos**, **Aulas**, **Labs** o **Biblioteca**.
- Pulsa **Ver ruta** en el destino que buscas.

Si aparece **«No encontramos una ruta disponible»**, la administración todavía no registró
ese camino. Pulsa **Elegir otro destino**.

## 7. Ruta calculada

Verás:
- desde dónde sales y a dónde vas;
- la **distancia** y el **tiempo** a pie;
- las **indicaciones paso a paso**, por ejemplo: «En Plaza Central, gira a la derecha y
  avanza 76 m»;
- un **mapa** con tu origen en verde, el destino en naranja y la ruta.

Pulsa **Ver recorrido en 3D**.

## 8. Recorrido 3D

Un **cubo naranja** recorre el camino sobre un modelo del campus. Arriba se muestra la
indicación del tramo actual.

| Botón | Acción |
|---|---|
| **Pausar / Continuar** | Detiene o sigue la animación |
| **Repetir** | Vuelve a empezar desde el origen |
| **Finalizar recorrido** | Pasa a la pantalla de llegada. Parpadea cuando el cubo llega |

Puedes **arrastrar** para girar la vista y usar la **rueda** del ratón (o pellizcar) para
acercar.

## 9. Llegada e historial

- En la pantalla **«¡Has llegado a tu destino!»**:
  - pulsa **Guardar en mi historial** para guardar la ruta;
  - pulsa **Volver al inicio** para empezar otra consulta.
- En **Historial** verás tus rutas, de la más reciente a la más antigua. **Repetir** vuelve a
  calcular esa ruta.
- Si entras a «Mi ruta» o al 3D sin haber hecho una consulta, verás **«Sin consulta
  seleccionada»**.

---

# Parte B · Administrador

Entra a **`/admin/`** con tu superusuario.

## Orden de carga

1. **Usuarios → Añadir usuario:** completa usuario, contraseña, nombre, **correo** (sirve para
   recuperar la cuenta), carrera y semestre.
   - ⚠️ **No marques** «Staff status» ni des permisos a un estudiante.
2. **Zonas:** nombre, descripción, latitud y longitud, e imagen opcional.
   - La zona **«Bloque A»** debe existir: es la que devuelve el reconocimiento simulado.
   - Desde la ficha de la zona también puedes agregar sus destinos.
3. **Destinos:** nombre, zona, tipo (aula, laboratorio, biblioteca u oficina) y coordenadas.
4. **Rutas:** elige el origen (zona) y el destino.
   - Deja **distancia** y **camino** vacíos para que se calculen solos.
   - Si después mueves una zona, usa la acción **«Recalcular distancia y camino»**.
5. **Pasillos del campus** (opcional): son los cruces por donde se camina (Plaza Central,
   Cruce Este…). Créalos con sus coordenadas y, en cada uno, agrega sus **conexiones** hacia
   otros pasillos. La distancia se calcula sola; escríbela solo si el camino real da un rodeo.
   Después usa la acción **«Recalcular distancia y camino»** en las rutas.
6. **Historial:** solo se puede ver; lo generan los estudiantes con el uso.

## Compartir el enlace con estudiantes

Para que otra persona entre desde su celular o computadora, aunque esté en otra red:

**Forma fácil:**
1. Haz doble clic en **`compartir_enlace.bat`**, en la carpeta `unemi_guide_ai`.
2. Espera a que aparezca el enlace `https://….trycloudflare.com`. Ya queda copiado.
3. Pégalo con `Ctrl + V` en WhatsApp o correo.
4. Cuando termines, presiona **Enter** en esa ventana para cerrar el enlace.

**Forma manual:**

1. **Terminal 1:** arranca el servidor con `python manage.py runserver`, dentro de `backend`
   y con el venv activo.
2. **Terminal 2:** ejecuta `cloudflared tunnel --url http://localhost:8000`.
   - La primera vez instálalo con `winget install --id Cloudflare.cloudflared` y vuelve a
     abrir PowerShell.
3. Copia el enlace `https://….trycloudflare.com` que aparece y compártelo.
4. Crea la cuenta del estudiante en **Usuarios** (sin «Staff status») y envíale su usuario y
   su contraseña.

**Ten en cuenta:**
- El enlace funciona solo mientras tu PC esté encendida y las dos terminales abiertas.
- El enlace cambia cada vez que ejecutas `cloudflared`.
- Cierra el túnel con `Ctrl + C` cuando termines.

Si están en tu misma red Wi-Fi, otra opción es `python manage.py runserver 0.0.0.0:8000` y
compartir `http://TU_IP:8000` (tu IP sale con `ipconfig`). En ese caso la cámara en vivo no
funciona y hay que usar «Subir desde galería».

## Datos de prueba

Para no cargar todo a mano, ejecuta este comando dentro de la carpeta `backend`:

```powershell
python manage.py loaddata datos_demo
```

Carga 5 zonas, 6 destinos, 3 pasillos con sus conexiones y 4 rutas. A propósito no hay ruta hacia «Secretaría General», para
poder probar la pantalla «Sin ruta disponible».
