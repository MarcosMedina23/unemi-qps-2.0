/**
 * ==========================================================================
 * UNEMI Guide AI · simulacion.js
 * --------------------------------------------------------------------------
 * Recorrido 3D con Three.js (r128, cargado desde CDN en index.html).
 *
 * Python calcula toda la escena (rutas/services.py → construir_escena):
 * posiciones de las zonas y puntos del camino en metros. Este archivo
 * solo DIBUJA: edificios, el camino y un cubo que se mueve del origen
 * al destino. Controles: Pausar/Continuar, Repetir y Finalizar.
 *
 * Coordenadas: X = este, Z = sur, Y = altura. 1 unidad = 1 metro.
 * ==========================================================================
 */
const Simulacion = (() => {
    "use strict";

    const COLORES = {
        cielo: 0xdbe7f5,
        cesped: 0x9cc78a,
        edificio: 0x0d47a1,
        origen: 0x2e7d32,
        destino: 0xff6f00,
        ruta: 0xff6f00,
        cubo: 0xff8f00,
    };
    const VELOCIDAD_M_POR_S = 25; // Acelerado para la demostración
    const FPS_MINIMOS = 30; // Meta del proyecto: simulación a 30 FPS o más
    const TAMANO_EDIFICIO = { ancho: 22, alto: 12, fondo: 16 };
    const SEPARACION_EDIFICIO = 14; // El edificio queda al norte de su plazoleta

    const contenedor = document.getElementById("escena-3d");
    const indicacion = document.getElementById("escena-indicacion");
    const error = document.getElementById("escena-error");
    const progreso = document.getElementById("escena-progreso");
    const botonPausar = document.getElementById("boton-pausar");
    const botonRepetir = document.getElementById("boton-repetir");
    const botonFinalizar = document.getElementById("boton-finalizar");
    const indicadorFps = document.getElementById("escena-fps");

    let alFinalizar = () => {};
    let contexto = null; // { renderer, escena, camara, controles, cubo, camino, tramos }
    let idAnimacion = null;
    let observador = null;
    const estado = { pausado: false, recorrido: 0, ultimoTiempo: null, paso: -1 };
    const medidorFps = { cuadros: 0, inicio: null };

    /** Cuenta los cuadros dibujados y muestra los FPS una vez por segundo. */
    function medirFps(tiempo) {
        if (medidorFps.inicio === null) medidorFps.inicio = tiempo;
        medidorFps.cuadros += 1;
        const transcurrido = tiempo - medidorFps.inicio;
        if (transcurrido < 1000) return;

        const fps = Math.round((medidorFps.cuadros * 1000) / transcurrido);
        indicadorFps.textContent = `${fps} FPS`;
        indicadorFps.classList.toggle("escena__fps--bajo", fps < FPS_MINIMOS);
        medidorFps.cuadros = 0;
        medidorFps.inicio = tiempo;
    }

    /* ------------------------------------------------------------------
     * Construcción de la escena
     * ---------------------------------------------------------------- */
    function crearEtiqueta(texto) {
        const lienzo = document.createElement("canvas");
        lienzo.width = 512;
        lienzo.height = 96;
        const dibujo = lienzo.getContext("2d");
        dibujo.fillStyle = "rgba(255, 255, 255, 0.92)";
        dibujo.fillRect(0, 8, 512, 80);
        dibujo.font = "600 40px 'IBM Plex Sans', sans-serif";
        dibujo.fillStyle = "#212121";
        dibujo.textAlign = "center";
        dibujo.textBaseline = "middle";
        dibujo.fillText(texto, 256, 50);

        const sprite = new THREE.Sprite(
            new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(lienzo), depthTest: false })
        );
        sprite.scale.set(26, 5, 1);
        sprite.renderOrder = 10;
        return sprite;
    }

    function agregarZonas(escena, zonas) {
        zonas.forEach((zona) => {
            let color = COLORES.edificio;
            if (zona.es_origen) color = COLORES.origen;
            if (zona.es_destino) color = COLORES.destino;

            const plazoleta = new THREE.Mesh(
                new THREE.CylinderGeometry(6, 6, 0.3, 32),
                new THREE.MeshLambertMaterial({ color: 0xffffff })
            );
            plazoleta.position.set(zona.x, 0.15, zona.z);
            escena.add(plazoleta);

            const edificio = new THREE.Mesh(
                new THREE.BoxGeometry(TAMANO_EDIFICIO.ancho, TAMANO_EDIFICIO.alto, TAMANO_EDIFICIO.fondo),
                new THREE.MeshStandardMaterial({ color, roughness: 0.6 })
            );
            edificio.position.set(zona.x, TAMANO_EDIFICIO.alto / 2, zona.z - SEPARACION_EDIFICIO);
            edificio.castShadow = true;
            escena.add(edificio);

            const etiqueta = crearEtiqueta(zona.nombre);
            etiqueta.position.set(zona.x, TAMANO_EDIFICIO.alto + 5, zona.z - SEPARACION_EDIFICIO);
            escena.add(etiqueta);
        });
    }

    function agregarCamino(escena, camino) {
        if (camino.length < 2) return;
        const trazo = new THREE.CurvePath();
        for (let i = 0; i < camino.length - 1; i += 1) {
            trazo.add(
                new THREE.LineCurve3(
                    new THREE.Vector3(camino[i].x, 0.6, camino[i].z),
                    new THREE.Vector3(camino[i + 1].x, 0.6, camino[i + 1].z)
                )
            );
        }
        escena.add(
            new THREE.Mesh(
                new THREE.TubeGeometry(trazo, 200, 0.8, 8, false),
                new THREE.MeshStandardMaterial({ color: COLORES.ruta, emissive: COLORES.ruta, emissiveIntensity: 0.3 })
            )
        );
    }

    function construir(datos) {
        const escena = new THREE.Scene();
        escena.background = new THREE.Color(COLORES.cielo);

        // Centro y tamaño del campus para ubicar el suelo y la cámara.
        const puntos = [...datos.zonas, ...datos.camino];
        const centroX = (Math.min(...puntos.map((p) => p.x)) + Math.max(...puntos.map((p) => p.x))) / 2;
        const centroZ = (Math.min(...puntos.map((p) => p.z)) + Math.max(...puntos.map((p) => p.z))) / 2;
        const extension = Math.max(80, ...puntos.map((p) => Math.hypot(p.x - centroX, p.z - centroZ)));

        escena.add(new THREE.HemisphereLight(0xffffff, 0x6f8f60, 0.6));
        const sol = new THREE.DirectionalLight(0xffffff, 0.6);
        sol.position.set(centroX + 60, 120, centroZ + 40);
        sol.castShadow = true;
        escena.add(sol);

        const suelo = new THREE.Mesh(
            new THREE.PlaneGeometry(extension * 4, extension * 4),
            new THREE.MeshLambertMaterial({ color: COLORES.cesped })
        );
        suelo.rotation.x = -Math.PI / 2;
        suelo.position.set(centroX, 0, centroZ);
        suelo.receiveShadow = true;
        escena.add(suelo);

        agregarZonas(escena, datos.zonas);
        agregarCamino(escena, datos.camino);

        // El cubo que recorre la ruta.
        const cubo = new THREE.Mesh(
            new THREE.BoxGeometry(4, 4, 4),
            new THREE.MeshStandardMaterial({ color: COLORES.cubo, roughness: 0.3 })
        );
        cubo.castShadow = true;
        escena.add(cubo);

        const camara = new THREE.PerspectiveCamera(50, 1, 0.5, 2000);
        camara.position.set(centroX + extension * 0.9, extension * 1.1, centroZ + extension * 1.1);

        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.shadowMap.enabled = true;
        contenedor.replaceChildren(renderer.domElement);

        let controles = null;
        if (typeof THREE.OrbitControls === "function") {
            controles = new THREE.OrbitControls(camara, renderer.domElement);
            controles.target.set(centroX, 0, centroZ);
            controles.enableDamping = true;
            controles.maxPolarAngle = Math.PI / 2.2; // No mirar bajo el suelo
            controles.update();
        } else {
            camara.lookAt(centroX, 0, centroZ);
        }

        // Distancia acumulada hasta cada punto del camino.
        const tramos = [0];
        for (let i = 1; i < datos.camino.length; i += 1) {
            const anterior = datos.camino[i - 1];
            const actual = datos.camino[i];
            tramos.push(tramos[i - 1] + Math.hypot(actual.x - anterior.x, actual.z - anterior.z));
        }

        return { renderer, escena, camara, controles, cubo, camino: datos.camino, tramos };
    }

    /* ------------------------------------------------------------------
     * Animación
     * ---------------------------------------------------------------- */
    function ajustarTamano() {
        if (!contexto) return;
        const { clientWidth: ancho, clientHeight: alto } = contenedor;
        if (!ancho || !alto) return;
        contexto.camara.aspect = ancho / alto;
        contexto.camara.updateProjectionMatrix();
        // "false" evita que Three.js escriba estilos en línea en el <canvas>.
        contexto.renderer.setSize(ancho, alto, false);
    }

    function posicionEn(recorrido) {
        const { camino, tramos } = contexto;
        if (camino.length === 1) return { x: camino[0].x, z: camino[0].z, indice: 0 };
        let indice = tramos.findIndex((valor) => valor > recorrido) - 1;
        if (indice < 0) indice = camino.length - 2;
        const largo = tramos[indice + 1] - tramos[indice] || 1;
        const avance = Math.min(1, (recorrido - tramos[indice]) / largo);
        return {
            x: camino[indice].x + (camino[indice + 1].x - camino[indice].x) * avance,
            z: camino[indice].z + (camino[indice + 1].z - camino[indice].z) * avance,
            indice,
        };
    }

    function actualizarBotonPausa() {
        botonPausar.textContent = estado.pausado ? "Continuar" : "Pausar";
    }

    function cuadro(tiempo) {
        const segundos = estado.ultimoTiempo === null ? 0 : (tiempo - estado.ultimoTiempo) / 1000;
        estado.ultimoTiempo = tiempo;

        const total = contexto.tramos[contexto.tramos.length - 1];
        if (!estado.pausado && estado.recorrido < total) {
            estado.recorrido = Math.min(total, estado.recorrido + VELOCIDAD_M_POR_S * Math.min(segundos, 0.1));
        }

        const posicion = posicionEn(estado.recorrido);
        contexto.cubo.position.set(posicion.x, 2.6, posicion.z);
        contexto.cubo.rotation.y += segundos * (estado.pausado ? 0 : 1.5);

        if (posicion.indice !== estado.paso) {
            estado.paso = posicion.indice;
            indicacion.textContent = contexto.camino[posicion.indice].instruccion;
        }
        progreso.value = total ? Math.round((estado.recorrido / total) * 100) : 100;

        if (estado.recorrido >= total && !botonFinalizar.classList.contains("boton--resaltado")) {
            indicacion.textContent = contexto.camino[contexto.camino.length - 1].instruccion;
            botonFinalizar.classList.add("boton--resaltado");
        }

        if (contexto.controles) contexto.controles.update();
        contexto.renderer.render(contexto.escena, contexto.camara);
        medirFps(tiempo);
        idAnimacion = requestAnimationFrame(cuadro);
    }

    function reiniciar() {
        Object.assign(estado, { pausado: false, recorrido: 0, ultimoTiempo: null, paso: -1 });
        Object.assign(medidorFps, { cuadros: 0, inicio: null });
        botonFinalizar.classList.remove("boton--resaltado");
        actualizarBotonPausa();
    }

    /* ------------------------------------------------------------------
     * API pública
     * ---------------------------------------------------------------- */
    function iniciar(datosEscena) {
        detener();
        if (typeof THREE === "undefined" || !datosEscena || datosEscena.camino.length === 0) {
            error.hidden = false;
            return;
        }
        error.hidden = true;
        contexto = construir(datosEscena);
        reiniciar();
        ajustarTamano();
        observador = new ResizeObserver(ajustarTamano);
        observador.observe(contenedor);
        idAnimacion = requestAnimationFrame(cuadro);
    }

    /** Libera la memoria de la GPU al salir de la pantalla. */
    function detener() {
        if (idAnimacion) cancelAnimationFrame(idAnimacion);
        idAnimacion = null;
        if (observador) observador.disconnect();
        observador = null;
        if (contexto) {
            contexto.renderer.dispose();
            contenedor.replaceChildren();
        }
        contexto = null;
    }

    botonPausar.addEventListener("click", () => {
        estado.pausado = !estado.pausado;
        actualizarBotonPausa();
    });
    botonRepetir.addEventListener("click", reiniciar);
    botonFinalizar.addEventListener("click", () => alFinalizar());

    return {
        /** @param {() => void} callback - Al pulsar "Finalizar recorrido". */
        configurar(callback) {
            alFinalizar = callback;
        },
        iniciar,
        detener,
    };
})();
