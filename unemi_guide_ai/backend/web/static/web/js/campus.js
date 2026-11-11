/**
 * ==========================================================================
 * UNEMI Guide AI · campus.js
 * --------------------------------------------------------------------------
 * Datos del campus UNEMI real (el MISMO modelo de Unity), leídos de
 * static/web/data/campus_unemi.json (lo genera unity/herramientas/gen_cs.py).
 *
 * Coordenadas del JSON: metros, X = este, Z = NORTE (igual que Unity).
 * La escena de la API usa Z = SUR, por eso aquí casi todo se dibuja con -Z.
 *
 * Lo usan ruta.js (mapa 2D) y simulacion.js (recorrido 3D).
 * ==========================================================================
 */
const Campus = (() => {
    "use strict";

    const url = document.getElementById("escena-3d").dataset.campus;
    let promesa = null;

    /** Descarga el JSON una sola vez (las siguientes llamadas usan la misma promesa). */
    function cargar() {
        if (!promesa) {
            promesa = fetch(url)
                .then((respuesta) => (respuesta.ok ? respuesta.json() : null))
                .catch(() => null);
        }
        return promesa;
    }

    /**
     * Gira un punto local (lx, lz) alrededor del centro.
     * La rotación es en grados y en sentido HORARIO visto desde arriba (como Unity).
     */
    function girar(cx, cz, lx, lz, grados) {
        const t = (grados * Math.PI) / 180;
        return [cx + lx * Math.cos(t) + lz * Math.sin(t), cz - lx * Math.sin(t) + lz * Math.cos(t)];
    }

    /** Las 4 esquinas [x, z] de un rectángulo con centro, medidas y rotación. */
    function esquinas(cx, cz, ancho, largo, rot) {
        const a = ancho / 2;
        const l = largo / 2;
        return [[-a, -l], [a, -l], [a, l], [-a, l]].map(([x, z]) => girar(cx, cz, x, z, rot));
    }

    /** Contorno de una elipse (estadio). */
    function elipse(cx, cz, ancho, largo, rot, pasos = 48) {
        const puntos = [];
        for (let i = 0; i < pasos; i += 1) {
            const u = (i / pasos) * Math.PI * 2;
            puntos.push(girar(cx, cz, (Math.cos(u) * ancho) / 2, (Math.sin(u) * largo) / 2, rot));
        }
        return puntos;
    }

    /** Contorno de un bloque curvo (V, W, X): borde exterior y luego el interior de regreso. */
    function arco(a, pasos = 16) {
        const borde = (radio, desde, hasta) => {
            const puntos = [];
            for (let i = 0; i <= pasos; i += 1) {
                const angulo = ((desde + ((hasta - desde) * i) / pasos) * Math.PI) / 180;
                puntos.push([a.cx + radio * Math.cos(angulo), a.cz + radio * Math.sin(angulo)]);
            }
            return puntos;
        };
        return [...borde(a.r_out, a.a0, a.a1), ...borde(a.r_in, a.a1, a.a0)];
    }

    /** Centro del bloque curvo (para poner su nombre). */
    function centroArco(a) {
        const medio = (((a.a0 + a.a1) / 2) * Math.PI) / 180;
        const radio = (a.r_in + a.r_out) / 2;
        return [a.cx + radio * Math.cos(medio), a.cz + radio * Math.sin(medio)];
    }

    /** Un tramo de calle (de a hasta b) como rectángulo con su ancho. */
    function tramo(a, b, ancho) {
        const dx = b[0] - a[0];
        const dz = b[1] - a[1];
        const largo = Math.hypot(dx, dz) || 1;
        // Vector a lo largo (extendido medio ancho en cada punta) y vector de costado
        const ux = (dx / largo) * (ancho / 2);
        const uz = (dz / largo) * (ancho / 2);
        const px = -uz;
        const pz = ux;
        return [
            [a[0] - ux + px, a[1] - uz + pz],
            [b[0] + ux + px, b[1] + uz + pz],
            [b[0] + ux - px, b[1] + uz - pz],
            [a[0] - ux - px, a[1] - uz - pz],
        ];
    }

    return { cargar, esquinas, elipse, arco, centroArco, tramo };
})();
