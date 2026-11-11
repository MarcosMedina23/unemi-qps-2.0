using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

namespace UNEMI.Campus
{
    /// <summary>
    /// Cámara para recorrer el campus (funciona con el Input Manager viejo y con el nuevo Input System).
    /// PC:  clic derecho + arrastrar = girar | clic izquierdo o rueda + arrastrar = mover
    ///      rueda = zoom | WASD / flechas = mover | Q / E = girar | F = seguir a la personita
    /// Celular: 1 dedo = mover | 2 dedos = zoom (pellizcar) y girar
    /// Mientras sigue a la personita, WASD mueve a la personita (lo lee PersonaCaminante).
    /// </summary>
    [RequireComponent(typeof(Camera))]
    public class CampusCameraController : MonoBehaviour
    {
        public Vector3 foco = new Vector3(0f, 0f, -40f);
        public float distancia = 480f;
        [Range(10f, 89f)] public float inclinacion = 60f;
        public float giro = 0f;

        public float distanciaMin = 8f;
        public float distanciaMax = 900f;
        public float sensibilidadGiro = 0.25f;
        public float velocidadTeclado = 0.6f;
        [Tooltip("Limita el foco a la zona del campus")]
        public Rect limites = new Rect(-350f, -380f, 800f, 850f);

        [Header("Seguir a la personita")]
        public Transform objetivo;
        public bool seguir;

        /// <summary>WASD / flechas de este cuadro (x = derecha, y = adelante).</summary>
        public Vector2 Teclas { get; private set; }

        Camera cam;
#if !ENABLE_INPUT_SYSTEM
        Vector2 ultimoMouse;
        bool hayUltimoMouse;
#endif

        void Awake()
        {
            cam = GetComponent<Camera>();
            Aplicar();
        }

        /// <summary>Centra la cámara en un punto (lo puede usar el GPS para enfocar un destino).</summary>
        public void EnfocarEn(Vector3 punto, float nuevaDistancia = 120f)
        {
            foco = new Vector3(punto.x, 0f, punto.z);
            distancia = Mathf.Clamp(nuevaDistancia, distanciaMin, distanciaMax);
            Aplicar();
        }

        /// <summary>La cámara va detrás de un objeto (la personita) mientras se mueve.</summary>
        public void Seguir(Transform quien, float nuevaDistancia = 40f)
        {
            objetivo = quien;
            seguir = quien != null;
            distancia = Mathf.Clamp(nuevaDistancia, distanciaMin, distanciaMax);
        }

        void LateUpdate()
        {
            Vector2 orbita = Vector2.zero, arrastre = Vector2.zero, teclas = Vector2.zero;
            float zoom = 0f, giroTeclas = 0f;
            bool alternarSeguir = false;
            LeerEntrada(ref orbita, ref arrastre, ref zoom, ref teclas, ref giroTeclas, ref alternarSeguir);
            Teclas = teclas;

            if (alternarSeguir) seguir = !seguir && objetivo != null;
            if (arrastre.sqrMagnitude > 4f) seguir = false;   // al arrastrar el mapa se deja de seguir

            giro += orbita.x + giroTeclas * 90f * Time.deltaTime;
            inclinacion = Mathf.Clamp(inclinacion - orbita.y, 10f, 89f);

            Quaternion yaw = Quaternion.Euler(0f, giro, 0f);
            Vector3 derecha = yaw * Vector3.right;
            Vector3 adelante = yaw * Vector3.forward;

            if (seguir && objetivo != null)
            {
                // El foco va suavemente hacia la personita
                Vector3 p = objetivo.position;
                foco = Vector3.Lerp(foco, new Vector3(p.x, 0f, p.z), 1f - Mathf.Exp(-6f * Time.deltaTime));
                teclas = Vector2.zero;   // las teclas las usa la personita
            }

            // Arrastrar mueve el mapa con el dedo / mouse
            float mundoPorPixel = 2f * distancia * Mathf.Tan(cam.fieldOfView * 0.5f * Mathf.Deg2Rad) / Mathf.Max(1, Screen.height);
            float factorVertical = 1f / Mathf.Max(0.3f, Mathf.Sin(inclinacion * Mathf.Deg2Rad));
            foco -= (derecha * arrastre.x + adelante * arrastre.y * factorVertical) * mundoPorPixel;

            // Teclado mueve la cámara
            foco += (derecha * teclas.x + adelante * teclas.y) * distancia * velocidadTeclado * Time.deltaTime;

            foco.x = Mathf.Clamp(foco.x, limites.xMin, limites.xMax);
            foco.z = Mathf.Clamp(foco.z, limites.yMin, limites.yMax);
            foco.y = 0f;

            distancia = Mathf.Clamp(distancia * (1f - zoom * 0.1f), distanciaMin, distanciaMax);
            Aplicar();
        }

        void Aplicar()
        {
            Quaternion r = Quaternion.Euler(inclinacion, giro, 0f);
            transform.SetPositionAndRotation(foco - r * Vector3.forward * distancia, r);
        }

        void LeerEntrada(ref Vector2 orbita, ref Vector2 arrastre, ref float zoom, ref Vector2 teclas, ref float giroTeclas, ref bool alternarSeguir)
        {
#if ENABLE_INPUT_SYSTEM
            // ---------- Nuevo Input System ----------
            var ts = Touchscreen.current;
            int toques = 0;
            Vector2 p0 = Vector2.zero, p1 = Vector2.zero, d0 = Vector2.zero, d1 = Vector2.zero;
            if (ts != null)
            {
                foreach (var t in ts.touches)
                {
                    if (!t.press.isPressed) continue;
                    if (toques == 0) { p0 = t.position.ReadValue(); d0 = t.delta.ReadValue(); }
                    else if (toques == 1) { p1 = t.position.ReadValue(); d1 = t.delta.ReadValue(); }
                    toques++;
                }
            }
            if (toques == 1) { arrastre += d0; return; }
            if (toques >= 2) { Gestos(p0, d0, p1, d1, ref orbita, ref zoom); return; }

            var mouse = Mouse.current;
            if (mouse != null)
            {
                Vector2 delta = mouse.delta.ReadValue();
                if (mouse.rightButton.isPressed) orbita += delta * sensibilidadGiro;
                else if (mouse.leftButton.isPressed || mouse.middleButton.isPressed) arrastre += delta;
                float rueda = mouse.scroll.ReadValue().y;
                if (Mathf.Abs(rueda) > 0.01f) zoom += Mathf.Sign(rueda);
            }

            var kb = Keyboard.current;
            if (kb != null)
            {
                if (kb.wKey.isPressed || kb.upArrowKey.isPressed) teclas.y += 1;
                if (kb.sKey.isPressed || kb.downArrowKey.isPressed) teclas.y -= 1;
                if (kb.dKey.isPressed || kb.rightArrowKey.isPressed) teclas.x += 1;
                if (kb.aKey.isPressed || kb.leftArrowKey.isPressed) teclas.x -= 1;
                if (kb.eKey.isPressed) giroTeclas += 1;
                if (kb.qKey.isPressed) giroTeclas -= 1;
                if (kb.fKey.wasPressedThisFrame) alternarSeguir = true;
            }
#elif ENABLE_LEGACY_INPUT_MANAGER
            // ---------- Input Manager clásico ----------
            if (Input.touchCount == 1)
            {
                var t = Input.GetTouch(0);
                if (t.phase == TouchPhase.Moved) arrastre += t.deltaPosition;
                hayUltimoMouse = false;
                return;
            }
            if (Input.touchCount >= 2)
            {
                var a = Input.GetTouch(0); var b = Input.GetTouch(1);
                Gestos(a.position, a.deltaPosition, b.position, b.deltaPosition, ref orbita, ref zoom);
                hayUltimoMouse = false;
                return;
            }

            Vector2 pos = Input.mousePosition;
            Vector2 deltaMouse = hayUltimoMouse ? pos - ultimoMouse : Vector2.zero;
            ultimoMouse = pos; hayUltimoMouse = true;
            if (Input.GetMouseButton(1)) orbita += deltaMouse * sensibilidadGiro;
            else if (Input.GetMouseButton(0) || Input.GetMouseButton(2)) arrastre += deltaMouse;
            float rueda = Input.mouseScrollDelta.y;
            if (Mathf.Abs(rueda) > 0.01f) zoom += Mathf.Sign(rueda);

            if (Input.GetKey(KeyCode.W) || Input.GetKey(KeyCode.UpArrow)) teclas.y += 1;
            if (Input.GetKey(KeyCode.S) || Input.GetKey(KeyCode.DownArrow)) teclas.y -= 1;
            if (Input.GetKey(KeyCode.D) || Input.GetKey(KeyCode.RightArrow)) teclas.x += 1;
            if (Input.GetKey(KeyCode.A) || Input.GetKey(KeyCode.LeftArrow)) teclas.x -= 1;
            if (Input.GetKey(KeyCode.E)) giroTeclas += 1;
            if (Input.GetKey(KeyCode.Q)) giroTeclas -= 1;
            if (Input.GetKeyDown(KeyCode.F)) alternarSeguir = true;
#endif
        }

        static void Gestos(Vector2 a, Vector2 da, Vector2 b, Vector2 db, ref Vector2 orbita, ref float zoom)
        {
            Vector2 aPrev = a - da, bPrev = b - db;
            float dPrev = (aPrev - bPrev).magnitude, dAhora = (a - b).magnitude;
            zoom += (dAhora - dPrev) * 0.01f;
            float angPrev = Mathf.Atan2(bPrev.y - aPrev.y, bPrev.x - aPrev.x) * Mathf.Rad2Deg;
            float angAhora = Mathf.Atan2(b.y - a.y, b.x - a.x) * Mathf.Rad2Deg;
            orbita.x -= Mathf.DeltaAngle(angPrev, angAhora);
        }
    }
}
