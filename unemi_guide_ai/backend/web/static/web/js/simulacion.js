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
    const rutaUnity = contenedor.dataset.unity || ""; // Vacío si no hay build de Unity

    let alFinalizar = () => {};
    let contexto = null; // { camino, tramos, renderer?, escena?, camara?, controles?, persona? }
    let idAnimacion = null;
    let observador = null;
    let intento = 0; // Evita dibujar una escena vieja si el usuario sale antes de que cargue
    const estado = { pausado: false, recorrido: 0, ultimoTiempo: null, paso: -1 };
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

    /** Mueve piernas y brazos según los metros que avanzó en este cuadro. */
    function animarPersona(persona, metros) {
        persona.fase += (metros / ESCALA_PERSONA) * 0.9 * Math.PI;
        const intensidad = metros > 0 ? 1 : 0;
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

        return { renderer, escena, camara, controles, persona, ...medirCamino(datos.camino) };
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
    function moverPersona(posicion) {
        const { persona, camara, controles } = contexto;
        const anterior = persona.grupo.position.clone();
        persona.grupo.position.set(posicion.x, 0, posicion.z);

        const dx = posicion.x - anterior.x;
        const dz = posicion.z - anterior.z;
        const metros = Math.hypot(dx, dz);
        if (metros > 0.001) persona.grupo.rotation.y = Math.atan2(dx, dz);
        animarPersona(persona, metros);

        if (controles) {
            camara.position.x += dx;
            camara.position.z += dz;
            controles.target.set(posicion.x, 0, posicion.z);
            controles.update();
        }
    }

    function cuadro(tiempo) {
        const segundos = estado.ultimoTiempo === null ? 0 : (tiempo - estado.ultimoTiempo) / 1000;
        estado.ultimoTiempo = tiempo;

        const total = contexto.tramos[contexto.tramos.length - 1];
        if (!estado.pausado && estado.recorrido < total) {
            estado.recorrido = Math.min(total, estado.recorrido + VELOCIDAD_M_POR_S * Math.min(segundos, 0.1));
        }

        const posicion = posicionEn(estado.recorrido);
        if (posicion.indice !== estado.paso) {
            estado.paso = posicion.indice;
            indicacion.textContent = contexto.camino[posicion.indice].instruccion;
        }
        progreso.value = total ? Math.round((estado.recorrido / total) * 100) : 100;

        if (estado.recorrido >= total && !botonFinalizar.classList.contains("boton--resaltado")) {
            indicacion.textContent = contexto.camino[contexto.camino.length - 1].instruccion;
            botonFinalizar.classList.add("boton--resaltado");
        }

        if (contexto.renderer) {
            moverPersona(posicion);
            contexto.renderer.render(contexto.escena, contexto.camara);
            medirFps(tiempo);
        }
        idAnimacion = requestAnimationFrame(cuadro);
    }

    function reiniciar() {
        Object.assign(estado, { pausado: false, recorrido: 0, ultimoTiempo: null, paso: -1 });
        Object.assign(medidorFps, { cuadros: 0, inicio: null });
        botonFinalizar.classList.remove("boton--resaltado");
        actualizarBotonPausa();
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
        return enviarAUnity("LoadWaypoints", JSON.stringify(ultimaEscena));
    }

    function cargarUnity() {
        if (cargaUnity) return cargaUnity;
        const lienzo = document.createElement("canvas");
        lienzo.id = "unity-canvas";
        contenedor.replaceChildren(lienzo);
        cargaUnity = new Promise((resolver, rechazar) => {
            const script = document.createElement("script");
            script.src = `${rutaUnity}.loader.js`;
            script.onload = () =>
                createUnityInstance(lienzo, {
                    dataUrl: `${rutaUnity}.data`,
                    frameworkUrl: `${rutaUnity}.framework.js`,
                    codeUrl: `${rutaUnity}.wasm`,
                    companyName: "UNEMI",
                    productName: "UNEMI Guide AI",
                    productVersion: "1.0",
                })
                    .then((instancia) => {
                        window.unityInstance = instancia;
                        resolver(instancia);
                    })
                    .catch(rechazar);
            script.onerror = rechazar;
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

        if (rutaUnity) {
            // ---- Unity: se muestra Unity y aquí solo avanzan la barra y las indicaciones
            error.hidden = true;
            contexto = medirCamino(datosEscena.camino);
            reiniciar();
            idAnimacion = requestAnimationFrame(cuadro);
            try {
                await cargarUnity();
                if (miIntento === intento) enviarEscenaAUnity();
            } catch (problema) {
                error.hidden = false;
            }
            return;
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
        reiniciar();
        ajustarTamano();
        observador = new ResizeObserver(ajustarTamano);
        observador.observe(contenedor);
        idAnimacion = requestAnimationFrame(cuadro);
    }

    /** Libera la memoria de la GPU al salir de la pantalla (Unity se queda cargado). */
    function detener() {
        intento += 1;
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
