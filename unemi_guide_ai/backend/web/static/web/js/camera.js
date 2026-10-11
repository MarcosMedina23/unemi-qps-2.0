/**
 * ==========================================================================
 * UNEMI Guide AI · camera.js
 * --------------------------------------------------------------------------
 * Pantalla "¿Dónde estoy?": cámara en vivo, botón "Tomar foto" y
 * "Subir desde galería".
 *
 * IMPORTANTE: los navegadores solo permiten la cámara en vivo en
 * "contextos seguros" (https:// o http://localhost). Si se abre la app
 * por http://IP_DE_LA_PC:8000 desde el celular, la cámara en vivo no
 * está disponible y se usa "Subir desde galería" (que en el celular
 * también permite tomar una foto). Con el túnel de Cloudflare (https)
 * la cámara en vivo sí funciona.
 * ==========================================================================
 */
const Camara = (() => {
    "use strict";

    const CALIDAD_JPEG = 0.9;

    const video = document.getElementById("camara-video");
    const lienzo = document.getElementById("camara-lienzo");
    const aviso = document.getElementById("camara-aviso");
    const botonTomarFoto = document.getElementById("boton-tomar-foto");
    const entradaGaleria = document.getElementById("entrada-galeria");

    let flujo = null; // MediaStream activo
    let alTenerFoto = () => {}; // Callback que define app.js

    function mostrarAviso(texto) {
        aviso.textContent = texto;
        aviso.hidden = false;
        video.hidden = true;
        botonTomarFoto.disabled = true;
    }

    /** Enciende la cámara trasera (si el navegador lo permite). */
    async function iniciar() {
        if (flujo) return;

        const soportaCamara =
            window.isSecureContext && navigator.mediaDevices && navigator.mediaDevices.getUserMedia;
        if (!soportaCamara) {
            mostrarAviso(
                "La cámara en vivo necesita una conexión segura (https). " +
                    "Usa «Subir desde galería» para tomar o elegir una foto."
            );
            return;
        }

        try {
            flujo = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: { ideal: "environment" } },
                audio: false,
            });
            video.srcObject = flujo;
            video.hidden = false;
            aviso.hidden = true;
            botonTomarFoto.disabled = false;
        } catch (error) {
            mostrarAviso(
                "No pudimos acceder a la cámara. Revisa los permisos del navegador " +
                    "o usa «Subir desde galería»."
            );
        }
    }

    /** Apaga la cámara al salir de la pantalla (ahorra batería). */
    function detener() {
        if (!flujo) return;
        flujo.getTracks().forEach((pista) => pista.stop());
        flujo = null;
        video.srcObject = null;
        botonTomarFoto.disabled = true;
    }

    /** Captura el cuadro actual del video como una imagen JPEG. */
    function tomarFoto() {
        if (!flujo || video.videoWidth === 0) return;
        lienzo.width = video.videoWidth;
        lienzo.height = video.videoHeight;
        lienzo.getContext("2d").drawImage(video, 0, 0, lienzo.width, lienzo.height);
        lienzo.toBlob(
            (blob) => {
                if (blob) alTenerFoto(new File([blob], "foto.jpg", { type: "image/jpeg" }));
            },
            "image/jpeg",
            CALIDAD_JPEG
        );
    }

    function elegirDeGaleria() {
        const archivo = entradaGaleria.files[0];
        entradaGaleria.value = ""; // Permite volver a elegir la misma foto.
        if (archivo) alTenerFoto(archivo);
    }

    botonTomarFoto.addEventListener("click", tomarFoto);
    entradaGaleria.addEventListener("change", elegirDeGaleria);

    return {
        /** @param {(foto: File) => void} callback - Se llama con cada foto nueva. */
        configurar(callback) {
            alTenerFoto = callback;
        },
        iniciar,
        detener,
    };
})();
