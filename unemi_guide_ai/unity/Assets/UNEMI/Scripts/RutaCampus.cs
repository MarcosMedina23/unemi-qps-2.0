using System.Collections.Generic;
using UnityEngine;

namespace UNEMI.Campus
{
    /// <summary>
    /// Conecta el campus 3D con UNEMI Guide AI: recibe la ruta, hace caminar a la personita
    /// por las calles del campus y muestra las indicaciones en pantalla.
    ///
    /// IMPORTANTE: el GameObject debe llamarse exactamente "RouteAnimator", porque la web
    /// le envía la ruta con  unityInstance.SendMessage("RouteAnimator", "LoadWaypoints", json)
    /// (ver backend/web/static/web/js/simulacion.js).
    ///
    /// Cómo se ubica la ruta en el campus:
    ///  1. Django ya calcula la ruta por las calles del campus (Dijkstra) y la manda en
    ///     metros con el MISMO (0, 0) del modelo 3D: se sigue tal cual (Z sur → -Z).
    ///  2. Si la ruta viene vacía, busca el destino por nombre y camina con GrafoCalles.
    /// </summary>
    public class RutaCampus : MonoBehaviour
    {
        [Header("Piezas de la escena (las asigna el generador)")]
        public PersonaCaminante persona;
        public CampusCameraController camara;
        public LineRenderer linea;
        public Transform meta;

        [Header("Recorrido")]
        public float velocidad = 6f;          // metros por segundo
        public float velocidadGiro = 540f;    // grados por segundo
        public string lugarDeInicio = "ENTRADA_PEATONAL";

        [Header("Demo al dar Play (sin la web)")]
        public bool demoAlIniciar = true;
        public string demoDestino = "K-301";

        [Tooltip("Nombres de Django que no coinciden con el campus 3D. Formato: Nombre en Django=Id en Unity")]
        public string[] alias = { "Bloque A=T", "Biblioteca Central=CRAI", "Biblioteca=CRAI", "FACI=T" };

        [Header("Pantalla")]
        public bool mostrarPanel = true;

        readonly List<Vector3> camino = new List<Vector3>();
        int indice;
        bool andando, pausado;
        string nombreDestino = "";
        string mensaje = "Toca un destino en la web o usa la demo.";

        float tiempoFps; int cuadrosFps; float fps;

        public bool EstaAndando => andando && !pausado;

        void Start()
        {
            Application.targetFrameRate = 60;
#if UNITY_WEBGL && !UNITY_EDITOR
            // Dentro de la página web: la ruta y los botones los pone la web
            demoAlIniciar = false;
            mostrarPanel = false;
#endif
            if (demoAlIniciar) IrA(demoDestino);
        }

        // ================================================================
        //  Métodos que llama la web con SendMessage (reciben un solo string)
        // ================================================================

        /// <summary>Recibe el campo "escena" de /api/rutas/calcular/ en JSON.</summary>
        public void LoadWaypoints(string json)
        {
            Escena escena = JsonUtility.FromJson<Escena>(json);
            if (escena == null) { mensaje = "No llegó una ruta válida."; return; }
            CargarEscena(escena);
        }

        /// <summary>Camina desde donde está la personita hasta un lugar ("K-301", "CDIP", "Bloque H"...).</summary>
        public void IrA(string destino)
        {
            CampusLocation lugar = BuscarLugar(destino);
            if (lugar == null) { mensaje = "No encontré \"" + destino + "\" en el campus 3D."; return; }

            Vector3 desde = persona != null ? persona.transform.position : InicioPorDefecto();
            Empezar(CaminoPorCalles(desde, null, lugar), lugar.nombre);
        }

        /// <summary>La web envía su velocidad para que la barra de progreso y Unity vayan juntas.</summary>
        public void SetVelocidad(string metrosPorSegundo)
        {
            float valor;
            if (float.TryParse(metrosPorSegundo, System.Globalization.NumberStyles.Float,
                               System.Globalization.CultureInfo.InvariantCulture, out valor) && valor > 0f)
                velocidad = valor;
        }

        public void Pause(string _ = "") { pausado = true; }
        public void Resume(string _ = "") { pausado = false; }

        public void Replay(string _ = "")
        {
            if (camino.Count == 0) return;
            Empezar(new List<Vector3>(camino), nombreDestino);
        }

        /// <summary>Lo usa ApiClient desde Unity de escritorio.</summary>
        public void LoadRoute(RouteResponse ruta)
        {
            if (ruta != null && ruta.escena != null) CargarEscena(ruta.escena);
        }

        // ================================================================
        //  Armar el camino
        // ================================================================

        void CargarEscena(Escena escena)
        {
            ZonaEscena zonaOrigen = null, zonaDestino = null;
            if (escena.zonas != null)
                foreach (var z in escena.zonas)
                {
                    if (z.es_origen) zonaOrigen = z;
                    if (z.es_destino) zonaDestino = z;
                }

            string nombre = !string.IsNullOrEmpty(escena.destino) ? escena.destino
                          : zonaDestino != null ? zonaDestino.nombre : "tu destino";

            CampusLocation origen = zonaOrigen != null ? BuscarLugar(zonaOrigen.nombre) : null;
            CampusLocation destino = BuscarLugar(escena.destino);
            if (destino == null && zonaDestino != null) destino = BuscarLugar(zonaDestino.nombre);

            // 1) El camino de Django (X = este, Z = sur → en Unity Z = norte)
            var puntos = new List<Vector3>();
            if (escena.camino != null)
                foreach (var p in escena.camino) puntos.Add(new Vector3(p.x, 0f, -p.z));
            if (puntos.Count >= 2)
            {
                Empezar(puntos, nombre);
                return;
            }

            // 2) Sin camino: se calcula aquí por las calles hasta el destino
            if (destino == null) { mensaje = "La ruta no trae puntos."; return; }
            Vector3 inicio = origen != null ? origen.PosicionDestino : InicioPorDefecto();
            Empezar(CaminoPorCalles(inicio, origen, destino), nombre);
        }

        /// <summary>Origen → calles (Dijkstra) → puerta del destino.</summary>
        List<Vector3> CaminoPorCalles(Vector3 desde, CampusLocation origen, CampusLocation destino)
        {
            List<Vector3> calles = GrafoCalles.Camino(desde, destino.PosicionDestino);
            Vector3 primeraCalle = calles.Count > 0 ? calles[0] : destino.PosicionDestino;
            Vector3 ultimaCalle = calles.Count > 0 ? calles[calles.Count - 1] : desde;

            var puntos = new List<Vector3>();
            puntos.Add(origen != null ? Puerta(origen, primeraCalle) : desde);
            puntos.AddRange(calles);
            puntos.Add(Puerta(destino, ultimaCalle));
            return puntos;
        }

        /// <summary>
        /// Punto de llegada de un lugar: en los edificios, el borde más cercano a la calle
        /// (como una puerta); en el resto (canchas, parqueos, entradas), su centro.
        /// </summary>
        static Vector3 Puerta(CampusLocation lugar, Vector3 desde)
        {
            bool esEdificio = lugar.tipo == TipoLugar.Bloque || lugar.tipo == TipoLugar.Edificio ||
                              lugar.tipo == TipoLugar.Servicio || lugar.tipo == TipoLugar.Aula;
            if (lugar.puntoAcceso != null || !esEdificio) return lugar.PosicionDestino;

            // El aula está dentro del bloque: se usan las paredes del bloque
            Transform edificio = lugar.tipo == TipoLugar.Aula && lugar.transform.parent != null ? lugar.transform.parent : lugar.transform;
            Collider[] paredes = edificio.GetComponentsInChildren<Collider>();
            if (paredes.Length == 0) return lugar.PosicionDestino;

            Vector3 desdeSuelo = new Vector3(desde.x, 0.5f, desde.z);
            Vector3 mejor = paredes[0].ClosestPoint(desdeSuelo);
            foreach (var c in paredes)
            {
                Vector3 p = c.ClosestPoint(desdeSuelo);
                if ((p - desdeSuelo).sqrMagnitude < (mejor - desdeSuelo).sqrMagnitude) mejor = p;
            }
            // Un metro y medio afuera de la pared, a nivel del suelo
            Vector3 haciaAfuera = desdeSuelo - mejor; haciaAfuera.y = 0f;
            Vector3 puerta = mejor + (haciaAfuera.sqrMagnitude > 0.01f ? haciaAfuera.normalized * 1.5f : Vector3.zero);
            return new Vector3(puerta.x, 0f, puerta.z);
        }

        CampusLocation BuscarLugar(string texto)
        {
            if (string.IsNullOrWhiteSpace(texto)) return null;
            foreach (string a in alias)
            {
                int igual = a.IndexOf('=');
                if (igual > 0 && string.Equals(a.Substring(0, igual).Trim(), texto.Trim(), System.StringComparison.OrdinalIgnoreCase))
                    return CampusLocation.Buscar(a.Substring(igual + 1));
            }
            return CampusLocation.Buscar(texto);
        }

        Vector3 InicioPorDefecto()
        {
            var lugar = CampusLocation.Buscar(lugarDeInicio);
            return lugar != null ? lugar.PosicionDestino : Vector3.zero;
        }

        // ================================================================
        //  Recorrido
        // ================================================================

        void Empezar(List<Vector3> puntos, string destino)
        {
            camino.Clear();
            foreach (var p in puntos) camino.Add(new Vector3(p.x, 0.12f, p.z)); // sobre la calle
            nombreDestino = destino;
            indice = 1;
            andando = camino.Count > 1;
            pausado = false;
            mensaje = "Camina hacia " + destino;

            if (persona != null)
            {
                persona.EnRuta = andando;
                persona.ColocarEn(camino[0]);
            }
            DibujarLinea();
            if (meta != null)
            {
                meta.gameObject.SetActive(true);
                meta.position = new Vector3(camino[camino.Count - 1].x, 0f, camino[camino.Count - 1].z);
            }
            if (camara != null && persona != null) camara.Seguir(persona.transform, 40f);
        }

        void Update()
        {
            MedirFps();
            if (!EstaAndando || persona == null) return;

            Transform t = persona.transform;
            Vector3 objetivo = camino[indice];
            t.position = Vector3.MoveTowards(t.position, objetivo, velocidad * Time.deltaTime);

            Vector3 direccion = objetivo - t.position; direccion.y = 0f;
            if (direccion.sqrMagnitude > 0.0001f)
                t.rotation = Quaternion.RotateTowards(t.rotation, Quaternion.LookRotation(direccion), velocidadGiro * Time.deltaTime);

            if ((t.position - objetivo).sqrMagnitude < 0.01f)
            {
                indice++;
                if (indice >= camino.Count) Llegar();
            }
        }

        void Llegar()
        {
            andando = false;
            persona.EnRuta = false;   // ahora se puede mover con WASD
            mensaje = "¡Llegaste a " + nombreDestino + "!";
        }

        /// <summary>Metros que faltan hasta el destino.</summary>
        float DistanciaRestante()
        {
            if (!andando || persona == null) return 0f;
            float total = Vector3.Distance(persona.transform.position, camino[indice]);
            for (int i = indice; i < camino.Count - 1; i++) total += Vector3.Distance(camino[i], camino[i + 1]);
            return total;
        }

        void DibujarLinea()
        {
            if (linea == null) return;
            linea.positionCount = camino.Count;
            for (int i = 0; i < camino.Count; i++)
                linea.SetPosition(i, new Vector3(camino[i].x, 0.35f, camino[i].z));
        }

        // ================================================================
        //  Panel en pantalla (indicaciones, botones y FPS)
        // ================================================================

        void MedirFps()
        {
            tiempoFps += Time.unscaledDeltaTime; cuadrosFps++;
            if (tiempoFps >= 1f) { fps = cuadrosFps / tiempoFps; tiempoFps = 0f; cuadrosFps = 0; }
        }

        void OnGUI()
        {
            if (!mostrarPanel) return;
            float escala = Mathf.Max(1f, Screen.height / 720f);   // se ve bien también en celular
            GUI.matrix = Matrix4x4.Scale(new Vector3(escala, escala, 1f));

            GUILayout.BeginArea(new Rect(10, 10, 330, 220), GUI.skin.box);
            GUILayout.Label("<b>UNEMI Guide AI</b>", new GUIStyle(GUI.skin.label) { richText = true, fontSize = 16 });
            GUILayout.Label(mensaje);
            if (andando) GUILayout.Label("Faltan " + Mathf.RoundToInt(DistanciaRestante()) + " m");

            GUILayout.BeginHorizontal();
            if (andando && GUILayout.Button(pausado ? "Continuar" : "Pausar")) pausado = !pausado;
            if (camino.Count > 1 && GUILayout.Button("Repetir")) Replay();
            if (camara != null && persona != null && GUILayout.Button(camara.seguir ? "Vista libre" : "Seguir (F)"))
            {
                if (camara.seguir) camara.seguir = false; else camara.Seguir(persona.transform, 40f);
            }
            GUILayout.EndHorizontal();

            GUILayout.Label(!andando && camara != null && camara.seguir
                ? "WASD / flechas: mover a la personita"
                : "F: seguir a la personita");

            var colorAntes = GUI.color;
            GUI.color = fps >= 30f ? Color.green : Color.red;
            GUILayout.Label(Mathf.RoundToInt(fps) + " FPS");
            GUI.color = colorAntes;
            GUILayout.EndArea();
        }
    }
}
