/**
 * ==========================================================================
 * UNEMI Guide AI · simulacion.js
 * --------------------------------------------------------------------------
 * Recorrido 3D del campus UNEMI real.
 *
 *  - Si existe el build WebGL de Unity (static/web/unity/Build/unemi.*),
 *    se muestra UNITY y se le envía la ruta con SendMessage.
 *  - Si no, se dibuja EL MISMO campus con Three.js (r128, desde CDN) usando
 *    campus_unemi.json: bloques con sus colores, bloques curvos V-W-X,
 *    calles, estero, canchas, estadio, parqueos, áreas verdes, accesos y el
 *    monumento. Una personita camina por la ruta que calculó Django.
 *
 * Dos modos (botones del panel "Direcciones"):
 *  - "Referencial": la personita camina sola por la ruta (demostración).
 *  - "A tiempo real": la personita sigue el GPS del celular (gps.js) y las
 *    direcciones avanzan según dónde está el estudiante.
 *
 * Coordenadas en Three.js: X = este, Y = altura, Z = SUR (1 unidad = 1 m).
 *   - La escena de la API ya viene así (x, z).
 *   - El JSON del campus usa Z = norte (como Unity), por eso se dibuja con -Z.
 * ==========================================================================
 */
const Simulacion = (() => {
    "use strict";

    const VELOCIDAD_M_POR_S = 15; // Acelerado para la demostración
    const FPS_MINIMOS = 30; // Meta del proyecto: simulación a 30 FPS o más
    const ESCALA_PERSONA = 2.5; // Más grande que la real para verla mejor

    // Modo "A tiempo real" (GPS)
    const VELOCIDAD_CAMINANDO = 1.3; // m/s de una persona real (para el tiempo estimado)
    const DISTANCIA_FUERA_DE_RUTA = 25; // metros: más lejos, se avisa "te saliste de la ruta"
    const DISTANCIA_LEJOS_DEL_CAMPUS = 400; // metros: más lejos, la personita no te sigue
    const RADIO_LLEGADA = 12; // metros al destino para decir "llegaste"
    const SALTO_MAXIMO_SUAVE = 60; // metros: un salto mayor del GPS se dibuja de golpe

    const COLORES = {
        cielo: 0xdce8f5,
        pasto: 0xb0de98,
        agua: 0x5dade2,
        cancha: 0x2e9e5b,
        parqueo: 0x9e9e9e,
        verde: 0x7cb342,
        arbol: 0x2e7d32,
        tronco: 0x6d4c41,
        pista: 0xc0563e,
        campo: 0x4caf50,
        graderio: 0x1565c0,
        calle: 0x6b6b6b,
        avenida: 0x4a4a4a,
        sendero: 0xe8dfc8,
        peatonal: 0xd9c9a3,
        estero: 0x3a7bd5,
        entrada: 0xe53935,
        entradaVehicular: 0x1e88e5,
        salidaVehicular: 0x8e24aa,
        monumento: 0xd7ccc8,
        ruta: 0xff6f00,
        origen: 0x2e7d32,
        destino: 0xe53935,
        piel: 0xf1c27d,
        cabello: 0x3e2723,
        camisa: 0x0d47a1,
        pantalon: 0x263238,
        mochila: 0xf57c00,
    };

    const contenedor = document.getElementById("escena-3d");
    const indicacion = document.getElementById("escena-indicacion");
    const error = document.getElementById("escena-error");
    const progreso = document.getElementById("escena-progreso");
    const botonPausar = document.getElementById("boton-pausar");
    const botonRepetir = document.getElementById("boton-repetir");
    const botonFinalizar = document.getElementById("boton-finalizar");
    const indicadorFps = document.getElementById("escena-fps");
    // Panel "Direcciones"
    const botonesModo = document.querySelectorAll("[data-modo]");
    const ayudaModo = document.getElementById("modo-ayuda");
    const estadoGps = document.getElementById("gps-estado");
    const pasoIcono = document.getElementById("paso-icono");
    const pasoTexto = document.getElementById("paso-texto");
    const pasoSiguiente = document.getElementById("paso-siguiente");
    const textoFaltan = document.getElementById("direcciones-faltan");
    const textoTiempo = document.getElementById("direcciones-tiempo");
    const listaDirecciones = document.getElementById("direcciones-lista");
    // URLs del build de Unity (las pone Django). Vacío si no hay build.
    const archivosUnity = {
        loader: contenedor.dataset.unityLoader || "",
        data: contenedor.dataset.unityData || "",
        framework: contenedor.dataset.unityFramework || "",
        codigo: contenedor.dataset.unityCodigo || "",
    };
    let usarUnity = Boolean(archivosUnity.loader); // Pasa a false si Unity no carga

    let alFinalizar = () => {};
    let contexto = null; // { camino, tramos, renderer?, escena?, camara?, controles?, persona? }
    let idAnimacion = null;
    let observador = null;
    let intento = 0; // Evita dibujar una escena vieja si el usuario sale antes de que cargue
    const estado = {
        modo: "referencial", // "referencial" | "tiempo-real" (se recuerda entre recorridos)
        pausado: false,
        recorrido: 0, // metros avanzados sobre la ruta
        ultimoTiempo: null,
        paso: -1,
        llego: false,
        gps: null, // Última lectura útil: { x, z, precision, indice, distanciaRuta }
        mostrada: null, // Posición dibujada de la personita (se acerca suave al GPS)
        panel: "", // Evita reescribir el panel si nada cambió
    };
    const AYUDA_MODO = {
        referencial: "La personita camina sola para mostrarte el camino.",
        "tiempo-real": "La personita se mueve contigo usando el GPS de tu celular. Camina y sigue las direcciones.",
    };
    const medidorFps = { cuadros: 0, inicio: null };
    const materiales = {};

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
     * Piezas básicas
     * ---------------------------------------------------------------- */
    /** Un material por color (se reutiliza: menos memoria y más FPS). */
    function material(color) {
        const clave = new THREE.Color(color).getHexString(); // "#2E7D32", 0x2e7d32 o THREE.Color
        if (!materiales[clave]) materiales[clave] = new THREE.MeshLambertMaterial({ color: new THREE.Color(color) });
        return materiales[clave];
    }

    /**
     * Levanta un contorno del plano (puntos [x, zNorte] del JSON) hasta "alto" metros.
     * Truco: la forma se dibuja en el plano XY y se acuesta con rotateX(-90°);
     * así el eje Y de la forma (norte) queda en -Z, que es justo lo que necesitamos.
     */
    function prisma(puntos, alto, color, base = 0) {
        const forma = new THREE.Shape(puntos.map(([x, z]) => new THREE.Vector2(x, z)));
        const geometria = new THREE.ExtrudeGeometry(forma, { depth: alto, bevelEnabled: false });
        geometria.rotateX(-Math.PI / 2);
        const malla = new THREE.Mesh(geometria, material(color));
        malla.position.y = base;
        return malla;
    }

    function caja(ancho, alto, fondo, color) {
        return new THREE.Mesh(new THREE.BoxGeometry(ancho, alto, fondo), material(color));
    }

    function cilindro(radio, alto, color) {
        return new THREE.Mesh(new THREE.CylinderGeometry(radio, radio, alto, 20), material(color));
    }

    function esfera(radio, color) {
        return new THREE.Mesh(new THREE.SphereGeometry(radio, 16, 12), material(color));
    }

    /** Cartel con fondo blanco que siempre mira a la cámara y mantiene su tamaño en pantalla. */
    function etiqueta(texto, { fondo = "rgba(255, 255, 255, 0.92)", color = "#1B2A41", alto = 0.032 } = {}) {
        const lienzo = document.createElement("canvas");
        const dibujo = lienzo.getContext("2d");
        const fuente = "600 34px 'IBM Plex Sans', sans-serif";
        dibujo.font = fuente;
        lienzo.width = Math.ceil(dibujo.measureText(texto).width) + 28;
        lienzo.height = 52;
        dibujo.font = fuente; // Cambiar el tamaño del canvas borra la fuente
        dibujo.fillStyle = fondo;
        dibujo.fillRect(0, 0, lienzo.width, lienzo.height);
        dibujo.fillStyle = color;
        dibujo.textAlign = "center";
        dibujo.textBaseline = "middle";
        dibujo.fillText(texto, lienzo.width / 2, lienzo.height / 2 + 1);

        const textura = new THREE.CanvasTexture(lienzo);
        textura.minFilter = THREE.LinearFilter;
        const sprite = new THREE.Sprite(
            new THREE.SpriteMaterial({ map: textura, depthTest: false, sizeAttenuation: false })
        );
        sprite.scale.set((alto * lienzo.width) / lienzo.height, alto, 1);
        sprite.center.set(0.5, 0); // El cartel queda encima del punto
        sprite.renderOrder = 10;
        return sprite;
    }

    function ponerEtiqueta(escena, texto, x, zNorte, altura, opciones) {
        if (!texto) return;
        const sprite = etiqueta(texto, opciones);
        sprite.position.set(x, altura, -zNorte);
        escena.add(sprite);
    }

    /** Número "al azar" pero siempre igual (los árboles no cambian de lugar). */
    function azarFijo(semilla) {
        let valor = semilla;
        return () => {
            valor = (valor * 9301 + 49297) % 233280;
            return valor / 233280;
        };
    }

    /* ------------------------------------------------------------------
     * Campus (campus_unemi.json)
     * ---------------------------------------------------------------- */
    function agregarCampus(escena, campus) {
        // Pasto de fondo
        const suelo = new THREE.Mesh(new THREE.PlaneGeometry(1400, 1400), material(COLORES.pasto));
        suelo.rotation.x = -Math.PI / 2;
        suelo.position.set(40, -0.05, 20);
        escena.add(suelo);

        // Estero y calles: cada tramo es un rectángulo plano
        const colorCalle = {
            calle: COLORES.calle,
            avenida: COLORES.avenida,
            sendero: COLORES.sendero,
            peatonal: COLORES.peatonal,
        };
        const lineas = [...campus.calles, { ...campus.estero, estilo: "estero" }];
        lineas.forEach((linea) => {
            const color = linea.estilo === "estero" ? COLORES.estero : colorCalle[linea.estilo];
            const altura = { sendero: 0.12, peatonal: 0.12, estero: 0.07 }[linea.estilo] || 0.1;
            for (let i = 0; i < linea.puntos.length - 1; i += 1) {
                escena.add(prisma(Campus.tramo(linea.puntos[i], linea.puntos[i + 1], linea.ancho), altura, color));
            }
            if (linea.nombre) {
                const [a, b] = [linea.puntos[0], linea.puntos[linea.puntos.length - 1]];
                ponerEtiqueta(escena, linea.nombre, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 3);
            }
        });

        // Áreas planas: parqueos, áreas verdes, canchas y piscina
        const estiloArea = {
            agua: [COLORES.agua, 0.18],
            cancha: [COLORES.cancha, 0.12],
            parqueo: [COLORES.parqueo, 0.06],
            verde: [COLORES.verde, 0.06],
        };
        campus.areas.forEach((a) => {
            const [color, alto] = estiloArea[a.estilo] || [COLORES.verde, 0.06];
            escena.add(prisma(Campus.esquinas(a.x, a.z, a.ancho, a.largo, a.rot), alto, color));
            ponerEtiqueta(escena, a.nombre, a.x, a.z, 3);
            if (a.estilo === "verde") agregarArboles(escena, a);
        });

        // Estadio: pista, cancha y graderío
        const e = campus.estadio;
        escena.add(prisma(Campus.elipse(e.x, e.z, e.ancho, e.largo, e.rot), 0.16, COLORES.pista));
        escena.add(prisma(Campus.elipse(e.x, e.z, e.ancho * 0.68, e.largo * 0.8, e.rot), 0.24, COLORES.campo));
        escena.add(prisma(Campus.esquinas(e.x - e.ancho / 2 + 6, e.z, 9, e.largo * 0.42, 0), 8, COLORES.graderio));
        ponerEtiqueta(escena, e.nombre, e.x, e.z, 10);

        // Edificios (cajas) con techo un poco más oscuro
        campus.edificios.forEach((b) => {
            escena.add(prisma(Campus.esquinas(b.x, b.z, b.ancho, b.largo, b.rot), b.alto, b.color));
            const techo = new THREE.Color(b.color).multiplyScalar(0.72);
            escena.add(prisma(Campus.esquinas(b.x, b.z, b.ancho * 0.92, b.largo * 0.92, b.rot), 0.3, techo, b.alto));
            ponerEtiqueta(escena, b.nombre, b.x, b.z, b.alto + 3);
        });

        // Bloques curvos V, W y X
        campus.arcos.forEach((a) => {
            escena.add(prisma(Campus.arco(a), a.alto, a.color));
            const [x, z] = Campus.centroArco(a);
            ponerEtiqueta(escena, a.nombre, x, z, a.alto + 3);
        });

        agregarAccesos(escena, campus.accesos);
        agregarMonumento(escena, campus.monumento);
    }

    function agregarArboles(escena, area) {
        const azar = azarFijo(area.id.length * 97 + Math.round(area.x));
        const cantidad = Math.max(4, Math.min(40, Math.round((area.ancho * area.largo) / 600)));
        for (let i = 0; i < cantidad; i += 1) {
            const lx = (azar() - 0.5) * area.ancho * 0.85;
            const lz = (azar() - 0.5) * area.largo * 0.85;
            const [x, z] = girarPunto(area.x, area.z, lx, lz, area.rot);
            const tronco = cilindro(0.3, 3, COLORES.tronco);
            tronco.position.set(x, 1.5, -z);
            const copa = esfera(2.3, COLORES.arbol);
            copa.position.set(x, 4.5, -z);
            escena.add(tronco, copa);
        }
    }

    /** Un punto local dentro de un área girada (misma regla que Campus.esquinas). */
    function girarPunto(cx, cz, lx, lz, grados) {
        const t = (grados * Math.PI) / 180;
        return [cx + lx * Math.cos(t) + lz * Math.sin(t), cz - lx * Math.sin(t) + lz * Math.cos(t)];
    }

    function agregarAccesos(escena, accesos) {
        const colorPorTipo = {
            Entrada: COLORES.entrada,
            EntradaVehicular: COLORES.entradaVehicular,
            SalidaVehicular: COLORES.salidaVehicular,
        };
        accesos.forEach((p) => {
            const color = colorPorTipo[p.tipo] || COLORES.entrada;
            const base = cilindro(3, 0.3, color);
            base.position.set(p.x, 0.15, -p.z);
            const poste = cilindro(0.4, 4, color);
            poste.position.set(p.x, 2, -p.z);
            escena.add(base, poste);
            if (p.tipo !== "Entrada") {
                // Pluma de la garita en los accesos vehiculares
                const pluma = caja(7, 0.35, 0.35, 0xffffff);
                pluma.position.set(p.x + 3.5, 2.8, -p.z);
                escena.add(pluma);
            }
            ponerEtiqueta(escena, p.nombre, p.x, p.z, 7);
        });
    }

    function agregarMonumento(escena, m) {
        const plaza = cilindro(7, 0.2, COLORES.monumento);
        plaza.position.set(m.x, 0.1, -m.z);
        const pedestal = caja(9, 1.5, 2.5, COLORES.monumento);
        pedestal.position.set(m.x, 0.95, -m.z);
        escena.add(plaza, pedestal);

        // Tres astas; la del centro lleva la bandera del Ecuador
        [-3.2, 0, 3.2].forEach((dx) => {
            const alto = dx === 0 ? 12 : 10;
            const asta = cilindro(0.09, alto, 0xe0e0e0);
            asta.position.set(m.x + dx, 1.7 + alto / 2, -m.z);
            escena.add(asta);
            const franjas = dx === 0 ? [[0xffd100, 0.8], [0x0033a0, 0.4], [0xef3340, 0.4]] : [[0x6cace4, 1.6]];
            let y = 1.7 + alto - 0.1;
            franjas.forEach(([color, h]) => {
                const tela = caja(2.4, h, 0.05, color);
                tela.position.set(m.x + dx + 1.3, y - h / 2, -m.z);
                escena.add(tela);
                y -= h;
            });
        });
        ponerEtiqueta(escena, m.nombre, m.x, m.z, 16);
    }

    /* ------------------------------------------------------------------
     * Ruta, marcadores y personita
     * ---------------------------------------------------------------- */
    function agregarCamino(escena, camino) {
        if (camino.length < 2) return;
        const trazo = new THREE.CurvePath();
        for (let i = 0; i < camino.length - 1; i += 1) {
            trazo.add(
                new THREE.LineCurve3(
                    new THREE.Vector3(camino[i].x, 0.5, camino[i].z),
                    new THREE.Vector3(camino[i + 1].x, 0.5, camino[i + 1].z)
                )
            );
        }
        escena.add(
            new THREE.Mesh(
                new THREE.TubeGeometry(trazo, Math.max(64, camino.length * 24), 1, 8, false),
                new THREE.MeshLambertMaterial({ color: COLORES.ruta, emissive: COLORES.ruta, emissiveIntensity: 0.35 })
            )
        );
    }

    /** Aro y poste en el punto de inicio (verde) y en el destino (rojo), con su nombre. */
    function agregarMarcador(escena, punto, color, texto) {
        const aro = cilindro(4, 0.3, color);
        aro.position.set(punto.x, 0.3, punto.z);
        const poste = cilindro(0.35, 9, color);
        poste.position.set(punto.x, 4.5, punto.z);
        const bola = esfera(1.6, color);
        bola.position.set(punto.x, 9.5, punto.z);
        escena.add(aro, poste, bola);
        const sprite = etiqueta(texto, { fondo: `#${new THREE.Color(color).getHexString()}`, color: "#FFFFFF", alto: 0.038 });
        sprite.position.set(punto.x, 12, punto.z);
        escena.add(sprite);
    }

    /** Pieza que gira desde arriba (cadera u hombro) para animar el paso. */
    function articulacion(grupo, x, y, largo, ancho, color) {
        const pivote = new THREE.Group();
        pivote.position.set(x, y, 0);
        const parte = caja(ancho, largo, ancho * 1.1, color);
        parte.position.y = -largo / 2;
        pivote.add(parte);
        grupo.add(pivote);
        return pivote;
    }

    /** La personita (misma idea que la de Unity): mira hacia +Z, la mochila va atrás. */
    function crearPersona() {
        const persona = new THREE.Group();
        const cuerpo = new THREE.Group();
        persona.add(cuerpo);

        const piernas = [
            articulacion(cuerpo, -0.12, 0.85, 0.85, 0.18, COLORES.pantalon),
            articulacion(cuerpo, 0.12, 0.85, 0.85, 0.18, COLORES.pantalon),
        ];
        const torso = caja(0.5, 0.7, 0.28, COLORES.camisa);
        torso.position.y = 1.2;
        const mochila = caja(0.4, 0.5, 0.15, COLORES.mochila);
        mochila.position.set(0, 1.22, -0.21);
        const cabeza = esfera(0.18, COLORES.piel);
        cabeza.position.y = 1.74;
        const cabello = esfera(0.19, COLORES.cabello);
        cabello.scale.set(1, 0.6, 1);
        cabello.position.set(0, 1.83, -0.02);
        cuerpo.add(torso, mochila, cabeza, cabello);
        const brazos = [
            articulacion(cuerpo, -0.32, 1.5, 0.62, 0.13, COLORES.camisa),
            articulacion(cuerpo, 0.32, 1.5, 0.62, 0.13, COLORES.camisa),
        ];

        // Aro amarillo en el piso para encontrarla rápido
        const aro = cilindro(0.8, 0.04, 0xffc400);
        aro.position.y = 0.05;
        persona.add(aro);
        persona.scale.setScalar(ESCALA_PERSONA);

        const cartel = etiqueta("Tú", { fondo: "#FFC400", color: "#1B2A41", alto: 0.03 });
        cartel.position.y = 2.6;
        persona.add(cartel);

        return { grupo: persona, cuerpo, piernas, brazos, fase: 0 };
    }

    /** Mueve piernas y brazos según los metros que avanzó en este cuadro (intensidad 0 = quieta). */
    function animarPersona(persona, metros, intensidad) {
        persona.fase += (metros / ESCALA_PERSONA) * 0.9 * Math.PI;
        const angulo = Math.sin(persona.fase) * 0.6 * intensidad;
        persona.piernas[0].rotation.x = angulo;
        persona.piernas[1].rotation.x = -angulo;
        persona.brazos[0].rotation.x = -angulo * 0.8;
        persona.brazos[1].rotation.x = angulo * 0.8;
        persona.cuerpo.position.y = Math.abs(Math.sin(persona.fase)) * 0.06 * intensidad;
    }

    /* ------------------------------------------------------------------
     * Construcción de la escena Three.js
     * ---------------------------------------------------------------- */
    function construir(datos, campus) {
        const escena = new THREE.Scene();
        escena.background = new THREE.Color(COLORES.cielo);
        escena.fog = new THREE.Fog(COLORES.cielo, 700, 1400);

        escena.add(new THREE.HemisphereLight(0xffffff, 0x7a9a6a, 0.75));
        const sol = new THREE.DirectionalLight(0xffffff, 0.55);
        sol.position.set(-200, 300, 150);
        escena.add(sol);

        if (campus) agregarCampus(escena, campus);
        agregarCamino(escena, datos.camino);

        const inicio = datos.camino[0];
        const final = datos.camino[datos.camino.length - 1];
        const origen = datos.zonas.find((z) => z.es_origen);
        agregarMarcador(escena, inicio, COLORES.origen, `Inicio: ${origen ? origen.nombre : "tu ubicación"}`);
        agregarMarcador(escena, final, COLORES.destino, `Destino: ${datos.destino || "tu destino"}`);

        const persona = crearPersona();
        persona.grupo.position.set(inicio.x, 0, inicio.z);
        escena.add(persona.grupo);

        // Círculo azul de precisión del GPS (solo en "A tiempo real")
        const precision = new THREE.Mesh(
            new THREE.CircleGeometry(1, 40),
            new THREE.MeshBasicMaterial({ color: 0x1e88e5, transparent: true, opacity: 0.2, depthWrite: false })
        );
        precision.rotation.x = -Math.PI / 2;
        precision.position.set(inicio.x, 0.25, inicio.z);
        precision.visible = false;
        escena.add(precision);

        // Cámara detrás y arriba de la personita
        const camara = new THREE.PerspectiveCamera(50, 1, 0.5, 3000);
        camara.position.set(inicio.x + 40, 70, inicio.z + 90);

        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        contenedor.replaceChildren(renderer.domElement);

        let controles = null;
        if (typeof THREE.OrbitControls === "function") {
            controles = new THREE.OrbitControls(camara, renderer.domElement);
            controles.target.set(inicio.x, 0, inicio.z);
            controles.enableDamping = true;
            controles.minDistance = 15;
            controles.maxDistance = 900;
            controles.maxPolarAngle = Math.PI / 2.2; // No mirar bajo el suelo
            controles.update();
        } else {
            camara.lookAt(inicio.x, 0, inicio.z);
        }

        return { renderer, escena, camara, controles, persona, precision, ...medirCamino(datos.camino) };
    }

    /** Distancia acumulada hasta cada punto del camino. */
    function medirCamino(camino) {
        const tramos = [0];
        for (let i = 1; i < camino.length; i += 1) {
            tramos.push(tramos[i - 1] + Math.hypot(camino[i].x - camino[i - 1].x, camino[i].z - camino[i - 1].z));
        }
        return { camino, tramos };
    }

    /* ------------------------------------------------------------------
     * Animación (sirve para Three.js y para Unity)
     * ---------------------------------------------------------------- */
    function ajustarTamano() {
        if (!contexto || !contexto.renderer) return;
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

    /** Mueve a la personita y hace que la cámara la siga (manteniendo el ángulo del usuario). */
    function moverPersona(posicion, segundos) {
        const { persona, camara, controles } = contexto;
        const anterior = persona.grupo.position.clone();
        persona.grupo.position.set(posicion.x, 0, posicion.z);

        const dx = posicion.x - anterior.x;
        const dz = posicion.z - anterior.z;
        const metros = Math.hypot(dx, dz);
        // Solo gira si de verdad avanzó (evita que tiemble con el ruido del GPS)
        if (metros > 0.02) persona.grupo.rotation.y = Math.atan2(dx, dz);
        const rapidez = segundos > 0 ? metros / segundos : 0;
        animarPersona(persona, metros, rapidez < 0.15 ? 0 : Math.min(1, rapidez));

        if (contexto.precision.visible) contexto.precision.position.set(posicion.x, 0.25, posicion.z);

        if (controles) {
            camara.position.x += dx;
            camara.position.z += dz;
            controles.target.set(posicion.x, 0, posicion.z);
            controles.update();
        }
    }

    /* ------------------------------------------------------------------
     * Modo "A tiempo real": del GPS a la ruta
     * ---------------------------------------------------------------- */
    /**
     * Punto de la ruta más cercano a (x, z).
     * Si dos tramos quedan a la misma distancia (la ruta pasa dos veces por
     * el mismo lugar), se prefiere el más cercano al avance anterior.
     */
    function proyectarEnRuta(x, z) {
        const { camino, tramos } = contexto;
        if (camino.length === 1) {
            return { recorrido: 0, indice: 0, distancia: Math.hypot(x - camino[0].x, z - camino[0].z) };
        }
        let mejor = null;
        for (let i = 0; i < camino.length - 1; i += 1) {
            const a = camino[i];
            const b = camino[i + 1];
            const vx = b.x - a.x;
            const vz = b.z - a.z;
            const largo2 = vx * vx + vz * vz;
            const t = largo2 ? Math.max(0, Math.min(1, ((x - a.x) * vx + (z - a.z) * vz) / largo2)) : 0;
            const distancia = Math.hypot(x - (a.x + vx * t), z - (a.z + vz * t));
            const recorrido = tramos[i] + Math.sqrt(largo2) * t;
            const puntaje = distancia + 0.05 * Math.abs(recorrido - estado.recorrido);
            if (!mejor || puntaje < mejor.puntaje) mejor = { puntaje, distancia, recorrido, indice: i };
        }
        return mejor;
    }

    function mostrarEstadoGps(texto, tipo = "info") {
        estadoGps.hidden = !texto;
        estadoGps.textContent = texto;
        estadoGps.className = `gps-estado gps-estado--${tipo}`;
    }

    function formatearDistancia(metros) {
        return metros >= 1000 ? `${(metros / 1000).toFixed(1)} km` : `${Math.round(metros)} m`;
    }

    /** Nueva lectura del GPS (ya en metros de la escena). */
    function alMoverseGps({ x, z, precision }) {
        if (!contexto || estado.modo !== "tiempo-real") return;
        const proyeccion = proyectarEnRuta(x, z);
        const final = contexto.camino[contexto.camino.length - 1];
        const alDestino = Math.hypot(x - final.x, z - final.z);
        const textoPrecision = precision ? ` · precisión ±${Math.round(precision)} m` : "";

        if (proyeccion.distancia > DISTANCIA_LEJOS_DEL_CAMPUS) {
            // Muy lejos: la personita espera en el inicio
            estado.gps = null;
            mostrarEstadoGps(
                `Estás a ${formatearDistancia(proyeccion.distancia)} de la ruta. Acércate a la UNEMI para que la personita te siga.`,
                "aviso"
            );
            return;
        }

        estado.gps = { x, z, precision, indice: proyeccion.indice, distanciaRuta: proyeccion.distancia };
        estado.recorrido = proyeccion.recorrido;
        enviarAUnity("PosicionGps", `${x.toFixed(2)},${z.toFixed(2)}`);

        if (!estado.llego && alDestino <= Math.max(RADIO_LLEGADA, Math.min(precision || 0, 25))) {
            estado.llego = true;
            estado.recorrido = contexto.tramos[contexto.tramos.length - 1];
        }

        if (estado.llego) {
            mostrarEstadoGps("¡Llegaste a tu destino! Pulsa «Finalizar recorrido».", "ok");
        } else if (proyeccion.distancia > DISTANCIA_FUERA_DE_RUTA) {
            mostrarEstadoGps(
                `Te saliste de la ruta (${Math.round(proyeccion.distancia)} m). Regresa a la línea naranja.`,
                "aviso"
            );
        } else if (precision > 30) {
            mostrarEstadoGps(`Señal GPS débil${textoPrecision}. Sal a un lugar abierto.`, "aviso");
        } else {
            mostrarEstadoGps(`GPS activo${textoPrecision}`, "ok");
        }
    }

    function alFallarGps(mensaje, grave) {
        if (estado.modo !== "tiempo-real") return;
        mostrarEstadoGps(mensaje, grave ? "error" : "aviso");
        if (grave) estado.gps = null;
    }

    /** Posición de la personita en este cuadro según el modo. */
    function posicionDelCuadro(segundos) {
        const total = contexto.tramos[contexto.tramos.length - 1];
        if (estado.modo === "referencial") {
            if (!estado.pausado && estado.recorrido < total) {
                estado.recorrido = Math.min(total, estado.recorrido + VELOCIDAD_M_POR_S * Math.min(segundos, 0.1));
            }
            estado.llego = estado.recorrido >= total;
            return posicionEn(estado.recorrido);
        }

        // A tiempo real: la personita va donde dice el GPS (con un movimiento suave)
        const gps = estado.gps;
        if (!gps) return posicionEn(0);
        let mostrada = estado.mostrada;
        if (!mostrada || Math.hypot(gps.x - mostrada.x, gps.z - mostrada.z) > SALTO_MAXIMO_SUAVE) {
            mostrada = { x: gps.x, z: gps.z };
        } else {
            const suavizado = Math.min(1, segundos * 3);
            mostrada = {
                x: mostrada.x + (gps.x - mostrada.x) * suavizado,
                z: mostrada.z + (gps.z - mostrada.z) * suavizado,
            };
        }
        estado.mostrada = mostrada;
        return { ...mostrada, indice: estado.llego ? contexto.camino.length - 1 : gps.indice };
    }

    /* ------------------------------------------------------------------
     * Panel "Direcciones" (al costado de la escena)
     * ---------------------------------------------------------------- */
    const ICONOS_PASO = {
        inicio: "M12 20V5M6 11l6-6 6 6",
        recto: "M12 20V5M6 11l6-6 6 6",
        derecha: "M7 20v-7a4 4 0 0 1 4-4h8M15 5l4 4-4 4",
        izquierda: "M17 20v-7a4 4 0 0 0-4-4H5M9 5 5 9l4 4",
        llegada: "M6 21V4M6 4h11l-2.5 4L17 12H6",
    };

    function iconoPaso(tipo) {
        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("viewBox", "0 0 24 24");
        svg.setAttribute("aria-hidden", "true");
        const trazo = document.createElementNS("http://www.w3.org/2000/svg", "path");
        trazo.setAttribute("d", ICONOS_PASO[tipo] || ICONOS_PASO.recto);
        svg.append(trazo);
        return svg;
    }

    /** Giro en el punto i (misma regla que rutas/services.py → tipo_de_giro). */
    function tipoDePaso(camino, i) {
        if (i === camino.length - 1) return "llegada";
        if (i === 0) return "inicio";
        const [a, b, c] = [camino[i - 1], camino[i], camino[i + 1]];
        const [x1, z1, x2, z2] = [b.x - a.x, b.z - a.z, c.x - b.x, c.z - b.z];
        const largos = Math.hypot(x1, z1) * Math.hypot(x2, z2);
        if (!largos) return "recto";
        const seno = (x1 * z2 - z1 * x2) / largos;
        if (Math.abs(seno) < 0.26) return "recto";
        return seno > 0 ? "derecha" : "izquierda";
    }

    /** Arma la lista de direcciones una vez por recorrido. */
    function armarDirecciones() {
        const { camino } = contexto;
        contexto.tipos = camino.map((_, i) => tipoDePaso(camino, i));
        listaDirecciones.replaceChildren(
            ...camino.map((punto, i) => {
                const item = document.createElement("li");
                item.className = "direcciones__paso";
                const icono = document.createElement("span");
                icono.className = `direcciones__icono direcciones__icono--${contexto.tipos[i]}`;
                icono.append(iconoPaso(contexto.tipos[i]));
                const texto = document.createElement("span");
                texto.textContent = punto.instruccion || "Continúa por el camino.";
                item.append(icono, texto);
                return item;
            })
        );
        estado.panel = "";
    }

    /** Actualiza el paso actual, lo que falta y la lista (solo si algo cambió). */
    function actualizarPanel(indice, total) {
        const { camino, tramos, tipos } = contexto;
        const paso = estado.llego ? camino.length - 1 : Math.min(indice, camino.length - 1);
        const faltan = Math.max(0, total - estado.recorrido);
        const siguiente = paso + 1 < camino.length ? Math.max(0, tramos[paso + 1] - estado.recorrido) : 0;
        const esperandoGps = estado.modo === "tiempo-real" && !estado.gps && !estado.llego;
        const clave = `${paso}|${Math.round(faltan)}|${Math.round(siguiente)}|${esperandoGps}`;
        if (clave === estado.panel) return;
        estado.panel = clave;

        pasoIcono.className = `paso-actual__icono direcciones__icono--${tipos[paso]}`;
        pasoIcono.replaceChildren(iconoPaso(tipos[paso]));
        pasoTexto.textContent = esperandoGps
            ? "Esperando tu ubicación…"
            : camino[paso].instruccion || "Continúa por el camino.";
        pasoSiguiente.textContent =
            !esperandoGps && paso + 1 < camino.length
                ? `En ${formatearDistancia(siguiente)}: ${camino[paso + 1].instruccion}`
                : "";
        if (estado.llego || esperandoGps) {
            textoFaltan.textContent = estado.llego ? "¡Llegaste!" : "—";
            textoTiempo.textContent = "—";
        } else {
            textoFaltan.textContent = formatearDistancia(faltan);
            textoTiempo.textContent = `${Math.max(1, Math.ceil(faltan / VELOCIDAD_CAMINANDO / 60))} min`;
        }

        const items = listaDirecciones.children;
        for (let i = 0; i < items.length; i += 1) {
            items[i].classList.toggle("direcciones__paso--hecho", i < paso);
            items[i].classList.toggle("direcciones__paso--actual", i === paso);
            if (i === paso) items[i].setAttribute("aria-current", "step");
            else items[i].removeAttribute("aria-current");
        }
        // Lleva el paso actual a la vista DENTRO de la lista (sin mover la página)
        const actual = items[paso];
        if (actual) {
            listaDirecciones.scrollTo({ top: actual.offsetTop - listaDirecciones.clientHeight / 3, behavior: "smooth" });
        }
    }

    function cuadro(tiempo) {
        const segundos = estado.ultimoTiempo === null ? 0 : (tiempo - estado.ultimoTiempo) / 1000;
        estado.ultimoTiempo = tiempo;

        const total = contexto.tramos[contexto.tramos.length - 1];
        const posicion = posicionDelCuadro(segundos);
        const paso = Math.min(posicion.indice, contexto.camino.length - 1);
        const esperandoGps = estado.modo === "tiempo-real" && !estado.gps && !estado.llego;

        if (estado.llego) {
            indicacion.textContent = contexto.camino[contexto.camino.length - 1].instruccion;
        } else if (esperandoGps) {
            indicacion.textContent = "Esperando tu ubicación GPS…";
            estado.paso = -1;
        } else if (paso !== estado.paso) {
            estado.paso = paso;
            indicacion.textContent = contexto.camino[paso].instruccion;
        }
        progreso.value = total ? Math.round((estado.recorrido / total) * 100) : 100;
        botonFinalizar.classList.toggle("boton--resaltado", estado.llego);
        actualizarPanel(paso, total);

        if (contexto.renderer) {
            contexto.precision.visible = estado.modo === "tiempo-real" && Boolean(estado.gps);
            if (estado.gps) contexto.precision.scale.setScalar(Math.max(3, Math.min(60, estado.gps.precision || 3)));
            moverPersona(posicion, segundos);
            contexto.renderer.render(contexto.escena, contexto.camara);
            medirFps(tiempo);
        }
        idAnimacion = requestAnimationFrame(cuadro);
    }

    function reiniciar() {
        Object.assign(estado, {
            pausado: false,
            recorrido: 0,
            ultimoTiempo: null,
            paso: -1,
            llego: false,
            gps: null,
            mostrada: null,
            panel: "",
        });
        Object.assign(medidorFps, { cuadros: 0, inicio: null });
        botonFinalizar.classList.remove("boton--resaltado");
        actualizarBotonPausa();
    }

    /** Aplica el modo elegido (botones, GPS y Unity) y empieza desde el inicio. */
    function aplicarModo() {
        const tiempoReal = estado.modo === "tiempo-real";
        botonesModo.forEach((boton) => {
            const activo = boton.dataset.modo === estado.modo;
            boton.classList.toggle("modo__boton--activo", activo);
            boton.setAttribute("aria-pressed", String(activo));
        });
        ayudaModo.textContent = AYUDA_MODO[estado.modo];
        botonPausar.hidden = tiempoReal;
        botonRepetir.hidden = tiempoReal;

        reiniciar();
        if (!contexto) return;
        if (tiempoReal) {
            enviarAUnity("Pause");
            mostrarEstadoGps("Buscando tu ubicación… acepta el permiso de ubicación.", "info");
            Gps.iniciar(ultimaEscena && ultimaEscena.referencia, alMoverseGps, alFallarGps);
        } else {
            Gps.detener();
            mostrarEstadoGps("");
            enviarAUnity("Replay");
        }
    }

    function cambiarModo(modo) {
        if (modo === estado.modo) return;
        estado.modo = modo;
        aplicarModo();
    }

    /* ------------------------------------------------------------------
     * Unity WebGL
     * ----------------------------------------------------------------
     * Si existe el build (static/web/unity/Build/unemi.loader.js), se carga
     * una sola vez y se guarda en window.unityInstance. La ruta se envía al
     * GameObject "RouteAnimator" (unity/Assets/UNEMI/Scripts/RutaCampus.cs).
     * ---------------------------------------------------------------- */
    const OBJETO_UNITY = "RouteAnimator";
    let ultimaEscena = null;
    let cargaUnity = null;

    function enviarAUnity(metodo, valor = "") {
        const unity = window.unityInstance;
        if (!unity || typeof unity.SendMessage !== "function") return false;
        unity.SendMessage(OBJETO_UNITY, metodo, valor);
        return true;
    }

    /** Envía los waypoints a Unity (se puede llamar cuando Unity termine de cargar). */
    function enviarEscenaAUnity() {
        if (!ultimaEscena) return false;
        enviarAUnity("SetVelocidad", String(VELOCIDAD_M_POR_S));
        const enviado = enviarAUnity("LoadWaypoints", JSON.stringify(ultimaEscena));
        // En "A tiempo real" Unity no camina solo: espera las posiciones del GPS
        if (enviado && estado.modo === "tiempo-real") enviarAUnity("Pause");
        return enviado;
    }

    function cargarUnity() {
        if (cargaUnity) return cargaUnity;
        const lienzo = document.createElement("canvas");
        lienzo.id = "unity-canvas";
        contenedor.replaceChildren(lienzo);
        cargaUnity = new Promise((resolver, rechazar) => {
            const script = document.createElement("script");
            script.src = archivosUnity.loader;
            script.onload = () =>
                createUnityInstance(lienzo, {
                    dataUrl: archivosUnity.data,
                    frameworkUrl: archivosUnity.framework,
                    codeUrl: archivosUnity.codigo,
                    companyName: "UNEMI",
                    productName: "UNEMI Guide AI",
                    productVersion: "1.0",
                })
                    .then((instancia) => {
                        window.unityInstance = instancia;
                        resolver(instancia);
                    })
                    .catch(rechazar);
            script.onerror = () => rechazar(new Error("No se pudo descargar el loader de Unity"));
            document.body.append(script);
        });
        return cargaUnity;
    }

    /* ------------------------------------------------------------------
     * API pública
     * ---------------------------------------------------------------- */
    async function iniciar(datosEscena) {
        detener();
        const miIntento = ++intento;
        ultimaEscena = datosEscena;
        if (!datosEscena || datosEscena.camino.length === 0) {
            error.hidden = false;
            return;
        }

        if (usarUnity) {
            // ---- Unity: se muestra Unity y aquí solo avanzan la barra y las indicaciones
            error.hidden = true;
            contexto = medirCamino(datosEscena.camino);
            armarDirecciones();
            aplicarModo();
            idAnimacion = requestAnimationFrame(cuadro);
            try {
                await cargarUnity();
                if (miIntento === intento) enviarEscenaAUnity();
                return;
            } catch (problema) {
                // Unity no cargó: se muestra el mismo campus con Three.js.
                console.warn("Unity WebGL no cargó, se usa Three.js:", problema);
                usarUnity = false;
                cargaUnity = null;
                if (miIntento !== intento) return;
                if (idAnimacion) cancelAnimationFrame(idAnimacion);
                idAnimacion = null;
                Gps.detener();
                contexto = null;
                contenedor.replaceChildren();
            }
        }

        // ---- Three.js: se dibuja el mismo campus
        if (typeof THREE === "undefined") {
            error.hidden = false;
            return;
        }
        error.hidden = true;
        const campus = await Campus.cargar();
        if (miIntento !== intento) return; // El usuario ya salió de la pantalla

        contexto = construir(datosEscena, campus);
        armarDirecciones();
        aplicarModo();
        ajustarTamano();
        observador = new ResizeObserver(ajustarTamano);
        observador.observe(contenedor);
        idAnimacion = requestAnimationFrame(cuadro);
    }

    /** Libera la memoria de la GPU al salir de la pantalla (Unity se queda cargado). */
    function detener() {
        intento += 1;
        Gps.detener(); // Deja de usar el GPS (y la batería) al salir de la pantalla
        if (idAnimacion) cancelAnimationFrame(idAnimacion);
        idAnimacion = null;
        if (observador) observador.disconnect();
        observador = null;
        if (contexto && contexto.renderer) {
            contexto.escena.traverse((objeto) => {
                if (objeto.geometry) objeto.geometry.dispose();
                if (objeto.isSprite) {
                    objeto.material.map.dispose(); // Los carteles tienen su propia textura
                    objeto.material.dispose();
                } else if (objeto.material && !Object.values(materiales).includes(objeto.material)) {
                    objeto.material.dispose(); // Ruta y círculo GPS (los colores comunes se reutilizan)
                }
            });
            contexto.renderer.dispose();
            contenedor.replaceChildren();
        }
        contexto = null;
    }

    botonPausar.addEventListener("click", () => {
        estado.pausado = !estado.pausado;
        enviarAUnity(estado.pausado ? "Pause" : "Resume");
        actualizarBotonPausa();
    });
    botonRepetir.addEventListener("click", () => {
        enviarAUnity("Replay");
        reiniciar();
    });
    botonFinalizar.addEventListener("click", () => alFinalizar());
    botonesModo.forEach((boton) => boton.addEventListener("click", () => cambiarModo(boton.dataset.modo)));

    return {
        /** @param {() => void} callback - Al pulsar "Finalizar recorrido". */
        configurar(callback) {
            alFinalizar = callback;
        },
        iniciar,
        detener,
        enviarEscenaAUnity,
    };
})();
