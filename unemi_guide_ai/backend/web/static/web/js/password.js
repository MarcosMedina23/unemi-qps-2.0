/**
 * ==========================================================================
 * UNEMI Guide AI · password.js
 * --------------------------------------------------------------------------
 * Agrega a cada campo de contraseña un botón con ícono de ojo para
 * mostrar u ocultar lo escrito. Se usa en el login y en "crear nueva
 * contraseña". Los estilos están en login.css (bloque .campo__ojo).
 * ==========================================================================
 */
(function () {
    "use strict";

    // Íconos SVG fijos (no contienen datos del usuario).
    const ICONO_OJO =
        '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>';
    const ICONO_OJO_TACHADO =
        '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17.9 17.9A10.4 10.4 0 0 1 12 19c-7 0-11-7-11-7a19 19 0 0 1 5-5.9M9.9 5.2A9.4 9.4 0 0 1 12 5c7 0 11 7 11 7a19 19 0 0 1-2.2 3.2M14.1 14.1a3 3 0 1 1-4.2-4.2"/><path d="M1 1l22 22"/></svg>';

    function agregarBoton(campo) {
        // Envuelve el input para poder ubicar el botón encima, a la derecha.
        const envoltura = document.createElement("span");
        envoltura.className = "campo__clave";
        campo.parentNode.insertBefore(envoltura, campo);
        envoltura.append(campo);

        const boton = document.createElement("button");
        boton.type = "button"; // Evita que envíe el formulario
        boton.className = "campo__ojo";
        envoltura.append(boton);

        function actualizar(visible) {
            campo.type = visible ? "text" : "password";
            boton.innerHTML = visible ? ICONO_OJO_TACHADO : ICONO_OJO;
            boton.setAttribute("aria-label", visible ? "Ocultar contraseña" : "Mostrar contraseña");
            boton.setAttribute("aria-pressed", String(visible));
        }

        boton.addEventListener("click", () => {
            actualizar(campo.type === "password");
            campo.focus();
        });
        actualizar(false);
    }

    document.querySelectorAll('input[type="password"]').forEach(agregarBoton);
})();
