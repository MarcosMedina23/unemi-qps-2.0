/**
 * ==========================================================================
 * UNEMI Guide AI · api.js
 * --------------------------------------------------------------------------
 * Único punto de comunicación con la API de Django (/api/...).
 *
 * - Envía la cookie de sesión (credentials: "same-origin").
 * - Agrega el token CSRF en las peticiones POST (cookie "csrftoken").
 * - Si la sesión venció (401/403), redirige al login.
 * - Nunca lanza excepciones: siempre devuelve { ok, estado, datos }.
 * ==========================================================================
 */
const Api = (() => {
    "use strict";

    const BASE = "/api";
    const MENSAJE_SIN_CONEXION = "No hay conexión con el servidor. Intenta de nuevo.";

    /** Lee una cookie por su nombre (se usa para el token CSRF). */
    function leerCookie(nombre) {
        const cookie = document.cookie
            .split(";")
            .map((parte) => parte.trim())
            .find((parte) => parte.startsWith(`${nombre}=`));
        return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
    }

    /**
     * Realiza una petición a la API.
     * @param {string} ruta - Ruta relativa a /api, ej.: "/zonas/".
     * @param {{metodo?: string, json?: object, formulario?: FormData}} opciones
     * @returns {Promise<{ok: boolean, estado: number, datos: any}>}
     */
    async function solicitar(ruta, { metodo = "GET", json = null, formulario = null } = {}) {
        const configuracion = {
            method: metodo,
            credentials: "same-origin",
            headers: { Accept: "application/json" },
        };

        if (metodo !== "GET") {
            configuracion.headers["X-CSRFToken"] = leerCookie("csrftoken");
        }
        if (json) {
            configuracion.headers["Content-Type"] = "application/json";
            configuracion.body = JSON.stringify(json);
        }
        if (formulario) {
            // Con FormData el navegador define el Content-Type (multipart).
            configuracion.body = formulario;
        }

        let respuesta;
        try {
            respuesta = await fetch(BASE + ruta, configuracion);
        } catch (error) {
            return { ok: false, estado: 0, datos: { detalle: MENSAJE_SIN_CONEXION } };
        }

        // Sesión vencida o inexistente: volver a iniciar sesión.
        if (respuesta.status === 401 || respuesta.status === 403) {
            window.location.assign("/login/?next=/");
            return { ok: false, estado: respuesta.status, datos: {} };
        }

        const datos = await respuesta.json().catch(() => ({}));
        return { ok: respuesta.ok, estado: respuesta.status, datos };
    }

    /* ------------------------------------------------------------------
     * Endpoints
     * ---------------------------------------------------------------- */
    return {
        /** GET /api/zonas/ */
        zonas: () => solicitar("/zonas/"),

        /** GET /api/destinos/ */
        destinos: () => solicitar("/destinos/"),

        /** POST /api/zonas/reconocer/ (multipart, campo "foto") */
        reconocerZona(foto) {
            const formulario = new FormData();
            formulario.append("foto", foto, foto.name || "foto.jpg");
            return solicitar("/zonas/reconocer/", { metodo: "POST", formulario });
        },

        /** POST /api/rutas/calcular/ */
        calcularRuta: (origenId, destinoId) =>
            solicitar("/rutas/calcular/", {
                metodo: "POST",
                json: { origen_id: origenId, destino_id: destinoId },
            }),

        /** GET /api/historial/ */
        historial: () => solicitar("/historial/"),

        /** GET /api/historial/{id}/ */
        detalleHistorial: (id) => solicitar(`/historial/${encodeURIComponent(id)}/`),

        /** POST /api/historial/ (la foto es opcional) */
        guardarHistorial(rutaId, foto) {
            const formulario = new FormData();
            formulario.append("ruta_id", rutaId);
            if (foto) formulario.append("foto_origen", foto, foto.name || "foto.jpg");
            return solicitar("/historial/", { metodo: "POST", formulario });
        },

        /** GET /api/usuarios/carreras/ */
        rankingCarreras: () => solicitar("/usuarios/carreras/"),
    };
})();
