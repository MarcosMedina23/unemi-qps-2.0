/**
 * ==========================================================================
 * UNEMI Guide AI · app.js
 * --------------------------------------------------------------------------
 * Coordina la página única:
 *   - Navegación entre pantallas con el "hash" de la URL (#inicio, #camara…),
 *     así funcionan los enlaces, el botón "Atrás" del navegador y el menú.
 *   - Estado de la consulta actual (foto, zona, ruta).
 *   - Flujo: foto → zona → destino → ruta → 3D → llegada → historial.
 *
 * Usa los módulos: Api (api.js), Camara (camera.js), ModuloRuta (ruta.js)
 * y Simulacion (simulacion.js).
 * ==========================================================================
 */
(function () {
    "use strict";

    const PANTALLA_INICIAL = "inicio";
    // Pantallas que necesitan una ruta calculada; sin ella se muestra "sin-datos".
    const REQUIEREN_RUTA = new Set(["ruta", "recorrido", "llegada"]);
    const DURACION_AVISO_MS = 4000;

    /** Estado de la consulta en curso (vive solo mientras la página está abierta). */
    const estado = {
        foto: null, // File de la última foto
        zona: null, // Zona reconocida (objeto de la API)
        ruta: null, // Ruta calculada (objeto de la API)
        guardadaEnHistorial: false,
    };

    let pantallaActual = null;

    const pantallas = document.querySelectorAll("[data-pantalla]");
    const enlacesNavegacion = document.querySelectorAll("[data-nav]");
    const capaCargando = document.getElementById("cargando");
    const textoCargando = document.getElementById("cargando-texto");
    const contenedorAvisos = document.getElementById("avisos");
    const botonGuardar = document.getElementById("boton-guardar-historial");

    /* ==================================================================
     * Utilidades de interfaz
     * ================================================================ */
    function cargando(activo, texto = "Cargando…") {
        textoCargando.textContent = texto;
        capaCargando.hidden = !activo;
    }

    /**
     * Muestra un aviso flotante que desaparece solo.
     * @param {string} mensaje
     * @param {"info"|"exito"|"error"} tipo
     */
    function avisar(mensaje, tipo = "info") {
        const aviso = document.createElement("p");
        aviso.className = `aviso aviso--${tipo}`;
        aviso.textContent = mensaje;
        contenedorAvisos.append(aviso);
        setTimeout(() => aviso.remove(), DURACION_AVISO_MS);
    }

    function crear(etiqueta, clase, texto) {
        const elemento = document.createElement(etiqueta);
        if (clase) elemento.className = clase;
        if (texto !== undefined) elemento.textContent = texto;
        return elemento;
    }

    /* ==================================================================
     * Navegación
     * ================================================================ */
    function irA(nombre) {
        if (window.location.hash === `#${nombre}`) {
            mostrarPantalla(nombre);
        } else {
            window.location.hash = nombre;
        }
    }

    function mostrarPantalla(nombreSolicitado) {
        let nombre = nombreSolicitado;
        const existe = [...pantallas].some((pantalla) => pantalla.dataset.pantalla === nombre);
        if (!existe) nombre = PANTALLA_INICIAL;
        if (REQUIEREN_RUTA.has(nombre) && !estado.ruta) nombre = "sin-datos";
        if (nombre === "zona" && !estado.zona) nombre = "sin-datos";

        // Al salir de una pantalla se liberan sus recursos.
        if (pantallaActual === "camara" && nombre !== "camara") Camara.detener();
        if (pantallaActual === "recorrido" && nombre !== "recorrido") Simulacion.detener();

        pantallas.forEach((pantalla) => {
            pantalla.hidden = pantalla.dataset.pantalla !== nombre;
        });
        enlacesNavegacion.forEach((enlace) => {
            if (enlace.dataset.nav === nombre) enlace.setAttribute("aria-current", "page");
            else enlace.removeAttribute("aria-current");
        });
        pantallaActual = nombre;
        window.scrollTo(0, 0);

        // Al entrar a cada pantalla se cargan sus datos.
        const alEntrar = {
            inicio: cargarRanking,
            camara: () => Camara.iniciar(),
            destinos: () => ModuloRuta.mostrarDestinos(estado.zona),
            recorrido: () => Simulacion.iniciar(estado.ruta.escena),
            llegada: prepararLlegada,
            historial: cargarHistorial,
        };
        if (alEntrar[nombre]) alEntrar[nombre]();
    }

    window.addEventListener("hashchange", () =>
        mostrarPantalla(window.location.hash.slice(1) || PANTALLA_INICIAL)
    );

    /* ==================================================================
     * 1. Inicio: ranking de carreras
     * ================================================================ */
    async function cargarRanking() {
        const lista = document.getElementById("ranking-lista");
        const vacio = document.getElementById("ranking-vacio");
        const respuesta = await Api.rankingCarreras();
        const filas = respuesta.ok ? respuesta.datos : [];

        lista.replaceChildren(
            ...filas.map((fila, posicion) => {
                const item = crear("li", posicion === 0 ? "ranking__item ranking__item--lider" : "ranking__item");
                const encabezado = crear("div", "ranking__fila");
                encabezado.append(
                    crear("span", "ranking__posicion", String(posicion + 1)),
                    crear("span", "ranking__carrera", fila.carrera),
                    crear("span", "ranking__total", `${fila.total} · ${Math.round(fila.porcentaje)} %`)
                );
                const barra = crear("meter", "ranking__barra");
                barra.min = 0;
                barra.max = 1;
                barra.value = fila.proporcion;
                barra.setAttribute("aria-label", `${fila.carrera}: ${fila.total} estudiantes`);
                item.append(encabezado, barra);
                return item;
            })
        );
        vacio.hidden = filas.length > 0;
    }

    /* ==================================================================
     * 2-3. Foto → reconocimiento de zona
     * ================================================================ */
    async function analizarFoto(foto) {
        estado.foto = foto;
        cargando(true, "Analizando tu foto…");
        const respuesta = await Api.reconocerZona(foto);
        cargando(false);

        if (respuesta.estado === 404) {
            irA("sin-datos");
            return;
        }
        if (!respuesta.ok) {
            const errores = respuesta.datos.foto || [respuesta.datos.detalle || "No pudimos procesar la foto."];
            avisar(errores.join(" "), "error");
            return;
        }

        const resultado = respuesta.datos;
        if (!resultado.reconocida) {
            irA("error-reconocimiento");
            return;
        }

        // Nueva consulta: se descarta la ruta anterior.
        estado.zona = resultado.zona;
        estado.ruta = null;
        mostrarResultadoZona(resultado, foto);
        irA("zona");
    }

    function mostrarResultadoZona(resultado, foto) {
        const imagen = document.getElementById("zona-foto");
        if (imagen.src.startsWith("blob:")) URL.revokeObjectURL(imagen.src);
        imagen.src = URL.createObjectURL(foto);

        const semaforo = document.getElementById("zona-semaforo");
        semaforo.className = `semaforo semaforo--${resultado.semaforo}`;
        semaforo.textContent = resultado.semaforo === "verde" ? "Confianza alta" : "Confianza media";

        document.getElementById("zona-mensaje").textContent = resultado.mensaje;
        document.getElementById("zona-confianza").value = resultado.confianza;
        document.getElementById("zona-confianza-texto").textContent = `${Math.round(resultado.confianza * 100)} %`;
        document.getElementById("zona-nota-simulada").hidden = !resultado.simulado;
        // Métrica del proyecto: reconocimiento en 5 s o menos.
        const tiempo =
            resultado.tiempo_ms < 1000
                ? `${resultado.tiempo_ms} ms`
                : `${(resultado.tiempo_ms / 1000).toFixed(2)} s`;
        document.getElementById("zona-tiempo").textContent =
            `Analizada en ${tiempo} · ${resultado.detecciones.length} detecciones`;
    }

    /* ==================================================================
     * 4-5. Destino → ruta calculada
     * ================================================================ */
    async function calcularRuta(origenId, destinoId) {
        cargando(true, "Calculando la ruta más corta…");
        const respuesta = await Api.calcularRuta(origenId, destinoId);
        cargando(false);

        if (respuesta.estado === 404) {
            irA("sin-ruta");
            return;
        }
        if (!respuesta.ok) {
            avisar(respuesta.datos.detalle || "No pudimos calcular la ruta.", "error");
            return;
        }
        estado.ruta = respuesta.datos;
        estado.guardadaEnHistorial = false;
        ModuloRuta.mostrarRuta(estado.ruta);
        irA("ruta");
    }

    function verRutaHacia(destino) {
        if (!estado.zona) {
            avisar("Primero toma una foto para saber dónde estás.", "info");
            irA("camara");
            return;
        }
        calcularRuta(estado.zona.id, destino.id);
    }

    /* ==================================================================
     * 7. Llegada y guardado en el historial
     * ================================================================ */
    function prepararLlegada() {
        document.getElementById("llegada-detalle").textContent =
            `${estado.ruta.destino.nombre} · ${Math.round(estado.ruta.distancia)} m recorridos.`;
        botonGuardar.disabled = estado.guardadaEnHistorial;
        botonGuardar.textContent = estado.guardadaEnHistorial ? "Guardado ✓" : "Guardar en mi historial";
    }

    async function guardarEnHistorial() {
        botonGuardar.disabled = true;
        const respuesta = await Api.guardarHistorial(estado.ruta.id, estado.foto);
        if (respuesta.ok) {
            estado.guardadaEnHistorial = true;
            botonGuardar.textContent = "Guardado ✓";
            avisar("Ruta guardada en tu historial.", "exito");
        } else {
            botonGuardar.disabled = false;
            avisar("No pudimos guardar la ruta. Intenta de nuevo.", "error");
        }
    }

    /* ==================================================================
     * 8. Historial
     * ================================================================ */
    const formatoFecha = new Intl.DateTimeFormat("es-EC", { dateStyle: "medium", timeStyle: "short" });

    async function cargarHistorial() {
        const lista = document.getElementById("historial-lista");
        const vacio = document.getElementById("historial-vacio");
        const respuesta = await Api.historial();
        const consultas = respuesta.ok ? respuesta.datos : [];

        lista.replaceChildren(
            ...consultas.map((consulta) => {
                const { ruta } = consulta;
                const item = crear("li", "historial__item");
                const datos = crear("div", "historial__datos");
                datos.append(
                    crear("span", "historial__ruta", `${ruta.origen.nombre} → ${ruta.destino.nombre}`),
                    crear(
                        "span",
                        "historial__meta",
                        `${formatoFecha.format(new Date(consulta.fecha))} · ${Math.round(ruta.distancia)} m · ${ruta.tiempo_minutos} min`
                    )
                );
                const repetir = crear("button", "boton boton--contorno boton--pequeno", "Repetir");
                repetir.type = "button";
                repetir.addEventListener("click", () => {
                    estado.zona = ruta.origen;
                    calcularRuta(ruta.origen.id, ruta.destino.id);
                });
                item.append(datos, repetir);
                return item;
            })
        );
        vacio.hidden = consultas.length > 0;
    }

    /* ==================================================================
     * Arranque
     * ================================================================ */
    Camara.configurar(analizarFoto);
    ModuloRuta.configurar(verRutaHacia);
    Simulacion.configurar(() => irA("llegada"));
    botonGuardar.addEventListener("click", guardarEnHistorial);

    mostrarPantalla(window.location.hash.slice(1) || PANTALLA_INICIAL);
})();
