/**
 * ==========================================================================
 * UNEMI Guide AI · gps.js
 * --------------------------------------------------------------------------
 * Ubicación real del celular para el modo "A tiempo real" del recorrido.
 *
 *  - Usa navigator.geolocation.watchPosition (se actualiza cada vez que el
 *    usuario se mueve).
 *  - Convierte latitud/longitud a los MISMOS metros de la escena 3D
 *    (X = este, Z = sur), con el punto de referencia que manda Django en
 *    escena.referencia (rutas/services.py → construir_escena).
 *  - Mantiene la pantalla encendida mientras se navega (Wake Lock), si el
 *    navegador lo permite.
 *
 * Importante: los navegadores solo dan la ubicación en HTTPS o en localhost.
 * En el celular funciona cuando la app está publicada con https (AWS).
 * ==========================================================================
 */
const Gps = (() => {
    "use strict";

    let idSeguimiento = null;
    let bloqueoPantalla = null;

    /** true si este navegador puede dar la ubicación en esta página. */
    function disponible() {
        return "geolocation" in navigator && window.isSecureContext;
    }

    /** Mensaje claro cuando el GPS no se puede usar o falla. */
    function explicarError(problema) {
        if (!("geolocation" in navigator)) return "Este navegador no tiene GPS.";
        if (!window.isSecureContext) {
            return "El GPS solo funciona cuando la app se abre con un enlace seguro (https). Mientras tanto usa el modo Referencial.";
        }
        switch (problema && problema.code) {
            case 1:
                return "Permiso de ubicación denegado. Actívalo desde el candado de la barra de direcciones.";
            case 2:
                return "No hay señal GPS. Activa la ubicación del celular y sal a un lugar abierto.";
            case 3:
                return "El GPS tarda en responder… seguimos intentando.";
            default:
                return "No se pudo obtener tu ubicación.";
        }
    }

    /** Latitud/longitud → metros de la escena (misma fórmula que vision/utils.py). */
    function aMetros(lat, lng, referencia) {
        const factor = Math.cos((referencia.lat * Math.PI) / 180);
        return {
            x: (lng - referencia.lng) * referencia.metros_por_grado * factor,
            z: -(lat - referencia.lat) * referencia.metros_por_grado,
        };
    }

    async function mantenerPantallaEncendida() {
        try {
            if ("wakeLock" in navigator && !bloqueoPantalla) {
                bloqueoPantalla = await navigator.wakeLock.request("screen");
                bloqueoPantalla.addEventListener("release", () => {
                    bloqueoPantalla = null;
                });
            }
        } catch (problema) {
            bloqueoPantalla = null; // No es grave: solo se apagaría la pantalla
        }
    }

    // El navegador suelta el Wake Lock al cambiar de pestaña; se pide de nuevo al volver.
    document.addEventListener("visibilitychange", () => {
        if (idSeguimiento !== null && document.visibilityState === "visible") mantenerPantallaEncendida();
    });

    /**
     * Empieza a seguir la ubicación.
     * @param {{lat:number,lng:number,metros_por_grado:number}} referencia
     * @param {(posicion:{x:number,z:number,precision:number}) => void} alMoverse
     * @param {(mensaje:string, grave:boolean) => void} alFallar
     */
    function iniciar(referencia, alMoverse, alFallar) {
        detener();
        if (!disponible() || !referencia) {
            alFallar(referencia ? explicarError(null) : "La ruta no trae la referencia del GPS.", true);
            return false;
        }
        idSeguimiento = navigator.geolocation.watchPosition(
            (lectura) => {
                const { latitude, longitude, accuracy } = lectura.coords;
                alMoverse({ ...aMetros(latitude, longitude, referencia), precision: accuracy || 0 });
            },
            (problema) => alFallar(explicarError(problema), problema.code !== 3),
            { enableHighAccuracy: true, maximumAge: 1000, timeout: 15000 }
        );
        mantenerPantallaEncendida();
        return true;
    }

    function detener() {
        if (idSeguimiento !== null) navigator.geolocation.clearWatch(idSeguimiento);
        idSeguimiento = null;
        if (bloqueoPantalla) bloqueoPantalla.release().catch(() => {});
        bloqueoPantalla = null;
    }

    return { disponible, iniciar, detener, aMetros };
})();
