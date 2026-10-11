/**
 * ==========================================================================
 * UNEMI Guide AI · ruta.js
 * --------------------------------------------------------------------------
 * - Pantalla "Lista de destinos": buscador, filtros y botón "Ver ruta".
 * - Pantalla "Ruta calculada": resumen, indicaciones y mapa SVG.
 *
 * Seguridad: los textos que vienen de la API se insertan con textContent
 * (nunca con innerHTML) para evitar inyección de código.
 * ==========================================================================
 */
const ModuloRuta = (() => {
    "use strict";

    const SVG_NS = "http://www.w3.org/2000/svg";
    const MARGEN_MAPA = 18; // metros alrededor del campus en el mapa

    const lista = document.getElementById("destinos-lista");
    const vacio = document.getElementById("destinos-vacio");
    const buscador = document.getElementById("destinos-buscador");
    const textoOrigen = document.getElementById("destinos-origen");
    const botonesFiltro = document.querySelectorAll("[data-filtro]");

    let destinos = null; // Caché: se piden a la API una sola vez
    let filtroActivo = "";
    let alVerRuta = () => {};

    /* ------------------------------------------------------------------
     * Utilidad: crear elementos con clase y texto en una línea
     * ---------------------------------------------------------------- */
    function crear(etiqueta, clase, texto) {
        const elemento = document.createElement(etiqueta);
        if (clase) elemento.className = clase;
        if (texto !== undefined) elemento.textContent = texto;
        return elemento;
    }

    function crearSvg(etiqueta, atributos) {
        const elemento = document.createElementNS(SVG_NS, etiqueta);
        Object.entries(atributos).forEach(([nombre, valor]) => elemento.setAttribute(nombre, valor));
        return elemento;
    }

    /* ------------------------------------------------------------------
     * Lista de destinos
     * ---------------------------------------------------------------- */
    function normalizar(texto) {
        // Quita tildes y mayúsculas para que "computacion" encuentre "Computación".
        return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    }

    function renderizarDestinos() {
        const texto = normalizar(buscador.value.trim());
        const visibles = (destinos || []).filter(
            (destino) =>
                (!filtroActivo || destino.tipo === filtroActivo) &&
                (!texto || normalizar(`${destino.nombre} ${destino.zona_nombre}`).includes(texto))
        );

        lista.replaceChildren(
            ...visibles.map((destino) => {
                const item = crear("li", "destino");
                const datos = crear("div", "destino__datos");
                datos.append(
                    crear("span", "destino__nombre", destino.nombre),
                    crear("span", "destino__meta", `${destino.tipo_display} · ${destino.zona_nombre}`)
                );
                const boton = crear("button", "boton boton--primario boton--pequeno", "Ver ruta");
                boton.type = "button";
                boton.addEventListener("click", () => alVerRuta(destino));
                item.append(crear("span", `destino__icono destino__icono--${destino.tipo}`), datos, boton);
                return item;
            })
        );
        vacio.hidden = visibles.length > 0;
    }

    function activarFiltro(boton) {
        filtroActivo = boton.dataset.filtro;
        botonesFiltro.forEach((otro) => {
            const activo = otro === boton;
            otro.classList.toggle("filtros__boton--activo", activo);
            otro.setAttribute("aria-pressed", String(activo));
        });
        renderizarDestinos();
    }

    /**
     * Muestra la lista de destinos.
     * @param {object|null} zonaOrigen - Zona reconocida (o null).
     */
    async function mostrarDestinos(zonaOrigen) {
        textoOrigen.textContent = zonaOrigen
            ? `Desde: ${zonaOrigen.nombre_completo}`
            : "Primero toma una foto en «¿Dónde estoy?» para saber desde dónde sales.";

        if (destinos === null) {
            const respuesta = await Api.destinos();
            destinos = respuesta.ok ? respuesta.datos : [];
        }
        renderizarDestinos();
    }

    /* ------------------------------------------------------------------
     * Ruta calculada
     * ---------------------------------------------------------------- */
    function dibujarMapa(escena) {
        const mapa = document.getElementById("ruta-mapa");
        const puntos = [...escena.zonas, ...escena.camino];
        const xs = puntos.map((p) => p.x);
        const zs = puntos.map((p) => p.z);
        const minX = Math.min(...xs) - MARGEN_MAPA;
        const minZ = Math.min(...zs) - MARGEN_MAPA;
        const ancho = Math.max(...xs) - Math.min(...xs) + MARGEN_MAPA * 2;
        const alto = Math.max(...zs) - Math.min(...zs) + MARGEN_MAPA * 2;
        const escala = Math.max(ancho, alto) / 100; // Tamaño de textos y puntos

        mapa.setAttribute("viewBox", `${minX} ${minZ} ${ancho} ${alto}`);
        const elementos = [];

        // Línea de la ruta
        elementos.push(
            crearSvg("polyline", {
                class: "mapa__ruta",
                points: escena.camino.map((p) => `${p.x},${p.z}`).join(" "),
                "stroke-width": 1.4 * escala,
            })
        );

        // Zonas con su nombre
        escena.zonas.forEach((zona) => {
            let clase = "mapa__zona";
            if (zona.es_origen) clase += " mapa__zona--origen";
            if (zona.es_destino) clase += " mapa__zona--destino";
            elementos.push(crearSvg("circle", { class: clase, cx: zona.x, cy: zona.z, r: 2.4 * escala }));
            const etiqueta = crearSvg("text", {
                class: "mapa__texto",
                x: zona.x,
                y: zona.z + 6 * escala,
                "font-size": 3.2 * escala,
            });
            etiqueta.textContent = zona.nombre;
            elementos.push(etiqueta);
        });

        // Punto exacto del destino
        const final = escena.camino[escena.camino.length - 1];
        elementos.push(crearSvg("circle", { class: "mapa__meta", cx: final.x, cy: final.z, r: 1.6 * escala }));

        mapa.replaceChildren(...elementos);
    }

    /** Llena la pantalla "Ruta calculada" con la respuesta de la API. */
    function mostrarRuta(ruta) {
        document.getElementById("ruta-desde").textContent = ruta.origen.nombre_completo;
        document.getElementById("ruta-hasta").textContent = ruta.destino.nombre;
        document.getElementById("ruta-distancia").textContent = `${Math.round(ruta.distancia)} m`;
        document.getElementById("ruta-tiempo").textContent = `${ruta.tiempo_minutos} min`;

        document
            .getElementById("ruta-indicaciones")
            .replaceChildren(
                ...ruta.camino_json.map((punto) =>
                    crear("li", "indicaciones__paso", punto.instruccion || "Continúa por el camino.")
                )
            );
        dibujarMapa(ruta.escena);
    }

    /* ------------------------------------------------------------------
     * Eventos
     * ---------------------------------------------------------------- */
    buscador.addEventListener("input", renderizarDestinos);
    botonesFiltro.forEach((boton) => boton.addEventListener("click", () => activarFiltro(boton)));

    return {
        /** @param {(destino: object) => void} callback - Al pulsar "Ver ruta". */
        configurar(callback) {
            alVerRuta = callback;
        },
        mostrarDestinos,
        mostrarRuta,
    };
})();
