using UnityEngine;

namespace UNEMI.Campus
{
    /// <summary>
    /// La personita del recorrido.
    ///  - Mueve piernas y brazos según la velocidad a la que se desplaza (animación de caminar).
    ///  - Mientras sigue una ruta, la mueve RutaCampus.
    ///  - Sin ruta y con la cámara siguiéndola (tecla F), se maneja con WASD / flechas,
    ///    choca con los edificios gracias al CharacterController.
    /// </summary>
    [RequireComponent(typeof(CharacterController))]
    public class PersonaCaminante : MonoBehaviour
    {
        [Header("Partes del cuerpo (las asigna el generador)")]
        public Transform piernaIzquierda;
        public Transform piernaDerecha;
        public Transform brazoIzquierdo;
        public Transform brazoDerecho;
        public Transform cuerpo;

        [Header("Movimiento manual")]
        public CampusCameraController camara;
        public float velocidadManual = 6f;
        public float gravedad = -20f;

        [Header("Animación")]
        public float anguloPaso = 35f;
        public float pasosPorMetro = 0.9f;

        CharacterController controlador;
        Vector3 posicionAnterior;
        float fase;
        float velocidadVertical;
        bool enRuta;

        /// <summary>True mientras RutaCampus la mueve (se apaga el CharacterController para moverla libremente).</summary>
        public bool EnRuta
        {
            get { return enRuta; }
            set
            {
                enRuta = value;
                Controlador.enabled = !value;
            }
        }

        CharacterController Controlador
        {
            get
            {
                if (controlador == null) controlador = GetComponent<CharacterController>();
                return controlador;
            }
        }

        void Start()
        {
            posicionAnterior = transform.position;
        }

        /// <summary>Pone a la personita en un punto de golpe (sin animación).</summary>
        public void ColocarEn(Vector3 punto)
        {
            bool activo = Controlador.enabled;
            Controlador.enabled = false;
            transform.position = punto;
            Controlador.enabled = activo;
            posicionAnterior = punto;
        }

        void Update()
        {
            if (!enRuta) MoverConTeclado();
            Animar();
        }

        void MoverConTeclado()
        {
            if (camara == null || !camara.seguir || !Controlador.enabled) return;

            // WASD relativo a hacia dónde mira la cámara
            Vector2 t = camara.Teclas;
            Vector3 direccion = Quaternion.Euler(0f, camara.giro, 0f) * new Vector3(t.x, 0f, t.y);
            direccion = Vector3.ClampMagnitude(direccion, 1f);

            velocidadVertical = Controlador.isGrounded ? -1f : velocidadVertical + gravedad * Time.deltaTime;
            Controlador.Move((direccion * velocidadManual + Vector3.up * velocidadVertical) * Time.deltaTime);

            if (direccion.sqrMagnitude > 0.01f)
                transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(direccion), 10f * Time.deltaTime);
        }

        /// <summary>Balancea piernas y brazos según cuánto se movió en este cuadro.</summary>
        void Animar()
        {
            Vector3 movimiento = transform.position - posicionAnterior;
            movimiento.y = 0f;
            posicionAnterior = transform.position;

            float velocidad = Time.deltaTime > 0f ? movimiento.magnitude / Time.deltaTime : 0f;
            float intensidad = Mathf.Clamp01(velocidad / 2f);   // 0 = quieta, 1 = caminando

            fase += movimiento.magnitude * pasosPorMetro * Mathf.PI;
            float angulo = Mathf.Sin(fase) * anguloPaso * intensidad;

            // Sin movimiento, las extremidades vuelven suavemente a su lugar
            if (intensidad < 0.05f) fase = Mathf.Lerp(fase, Mathf.Round(fase / Mathf.PI) * Mathf.PI, 10f * Time.deltaTime);

            Girar(piernaIzquierda, angulo);
            Girar(piernaDerecha, -angulo);
            Girar(brazoIzquierdo, -angulo * 0.8f);
            Girar(brazoDerecho, angulo * 0.8f);

            if (cuerpo != null)   // pequeño rebote al caminar
                cuerpo.localPosition = new Vector3(0f, Mathf.Abs(Mathf.Sin(fase)) * 0.06f * intensidad, 0f);
        }

        static void Girar(Transform parte, float angulo)
        {
            if (parte != null) parte.localRotation = Quaternion.Euler(angulo, 0f, 0f);
        }
    }
}
