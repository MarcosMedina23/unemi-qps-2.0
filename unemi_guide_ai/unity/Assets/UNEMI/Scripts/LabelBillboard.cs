using UnityEngine;

namespace UNEMI.Campus
{
    /// <summary>
    /// Cartel con el nombre de cada lugar: siempre mira a la cámara y ajusta su fondo blanco al texto.
    /// </summary>
    [ExecuteAlways]
    public class LabelBillboard : MonoBehaviour
    {
        public enum Modo
        {
            MirarCamara,     // gira con la cámara (vista 3D)
            PlanoHaciaNorte  // acostado en el suelo, como un mapa (vista cenital)
        }

        public Modo modo = Modo.MirarCamara;

        [Tooltip("Mantiene un tamaño parecido en pantalla al alejar la cámara")]
        public bool escalarConDistancia = true;

        [Tooltip("Distancia de cámara a la que el cartel tiene su tamaño original")]
        public float distanciaReferencia = 250f;

        [Header("Cartel")]
        public TextMesh texto;
        public Transform fondo;
        public float margen = 1.5f;

        Camera cam;
        Vector3 escalaBase;
        bool escalaGuardada;
        string textoAjustado;

        void LateUpdate()
        {
            AjustarFondo();
            if (!Application.isPlaying) return;   // en el editor no se mueve nada

            if (!escalaGuardada) { escalaBase = transform.localScale; escalaGuardada = true; }

            if (modo == Modo.PlanoHaciaNorte)
            {
                transform.rotation = Quaternion.Euler(90f, 0f, 0f);
                return;
            }

            if (cam == null) cam = Camera.main;
            if (cam == null) return;

            transform.rotation = cam.transform.rotation;

            if (escalarConDistancia)
            {
                float d = Vector3.Distance(cam.transform.position, transform.position);
                float f = Mathf.Clamp(d / distanciaReferencia, 0.35f, 2.5f);
                transform.localScale = escalaBase * f;
            }
        }

        /// <summary>Hace que el fondo blanco tenga el tamaño exacto del texto (una vez por texto).</summary>
        void AjustarFondo()
        {
            if (texto == null || fondo == null || textoAjustado == texto.text) return;
            var r = texto.GetComponent<MeshRenderer>();
            if (r == null) return;

            Bounds b;
#if UNITY_2021_2_OR_NEWER
            b = r.localBounds;
#else
            Quaternion rot = transform.rotation;
            transform.rotation = Quaternion.identity;
            b = r.bounds;
            b.center = texto.transform.InverseTransformPoint(b.center);
            Vector3 s = texto.transform.lossyScale;
            b.size = new Vector3(b.size.x / s.x, b.size.y / s.y, b.size.z / s.z);
            transform.rotation = rot;
#endif
            if (b.size.x < 0.01f) return; // el texto aún no se ha generado

            Vector3 escala = new Vector3(b.size.x + margen * 2f, b.size.y + margen, 1f);
            Vector3 pos = new Vector3(b.center.x, b.center.y, fondo.localPosition.z);
            if ((fondo.localScale - escala).sqrMagnitude > 0.0001f) fondo.localScale = escala;
            if ((fondo.localPosition - pos).sqrMagnitude > 0.0001f) fondo.localPosition = pos;
            textoAjustado = texto.text;
        }
    }
}
