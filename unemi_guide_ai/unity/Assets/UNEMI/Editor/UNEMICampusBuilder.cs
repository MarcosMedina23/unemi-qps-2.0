using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace UNEMI.Campus.EditorTools
{
    /// <summary>
    /// Menú  UNEMI > Generar Campus 3D
    /// Construye todo el campus en la escena abierta a partir de CampusData.cs.
    /// </summary>
    public static class UNEMICampusBuilder
    {
        const string NombreRaiz = "UNEMI_Campus";
        const string CarpetaMateriales = "Assets/UNEMI/Materiales";
        const string CarpetaEscenas = "Assets/UNEMI/Escenas";

        // Tamaño de las letras de los nombres (metros). Cambia esto si los ves muy grandes o pequeños.
        const float AlturaLetraBloque = 4f;
        const float AlturaLetraArea = 5f;
        const int TamanoFuente = 64;

        // Colores generales (los edificios traen su propio color desde CampusData.cs)
        static readonly Dictionary<string, string> Estilos = new Dictionary<string, string>
        {
            { "suelo",       "B0DE98" },   // pasto
            { "techo",       "8D8D8D" },
            { "agua",        "5DADE2" },
            { "pista",       "C0563E" },
            { "campo",       "4CAF50" },
            { "graderio",    "1565C0" },
            { "cancha",      "2E9E5B" },
            { "verde",       "7CB342" },
            { "arbol",       "2E7D32" },
            { "tronco",      "6D4C41" },
            { "parqueo",     "9E9E9E" },
            { "linea",       "FFFFFF" },
            { "calle",       "6B6B6B" },
            { "avenida",     "4A4A4A" },
            { "sendero",     "E8DFC8" },
            { "peatonal",    "D9C9A3" },   // paseos peatonales entre bloques
            { "estero",      "3A7BD5" },
            { "entrada",     "E53935" },
            { "entrada_veh", "1E88E5" },
            { "salida_veh",  "8E24AA" },
            { "monumento",   "D7CCC8" },
            { "asta",        "E0E0E0" },
            { "ec_amarillo", "FFD100" },
            { "ec_azul",     "0033A0" },
            { "ec_rojo",     "EF3340" },
            { "celeste",     "6CACE4" },
            { "blanco",      "FFFFFF" },
            { "destacado",   "F57C00" },
            // Personita y recorrido
            { "piel",        "F1C27D" },
            { "cabello",     "3E2723" },
            { "camisa",      "0D47A1" },
            { "pantalon",    "263238" },
            { "zapato",      "212121" },
            { "mochila",     "F57C00" },
            { "ruta",        "FFC400" },
            { "meta",        "E53935" },
        };

        static readonly Color ColorTexto = Hex("1B2A41");
        static readonly Color ColorCielo = Hex("DCE8F5");

        static Dictionary<string, Material> cache;
        static Shader shaderLit, shaderUnlit;
        static Font fuente;

        // ------------------------------------------------------------------ Menús

        [MenuItem("UNEMI/Generar Campus 3D", priority = 1)]
        public static void Generar()
        {
            var viejo = GameObject.Find(NombreRaiz);
            if (viejo != null)
            {
                if (!EditorUtility.DisplayDialog("Campus UNEMI",
                        "Ya existe un campus en la escena. ¿Quieres reemplazarlo?", "Reemplazar", "Cancelar"))
                    return;
                Undo.DestroyObjectImmediate(viejo);
            }

            PrepararShaders();
            fuente = CargarFuente();

            var raiz = new GameObject(NombreRaiz);
            Undo.RegisterCreatedObjectUndo(raiz, "Generar campus UNEMI");
            raiz.AddComponent<CampusGeoReference>();

            Transform gSuelo = Grupo(raiz, "Suelo");
            Transform gBloques = Grupo(raiz, "Bloques");
            Transform gBanos = Grupo(raiz, "Baños");
            Transform gDeportes = Grupo(raiz, "Deportes");
            Transform gParqueos = Grupo(raiz, "Estacionamientos");
            Transform gVerdes = Grupo(raiz, "Areas Verdes");
            Transform gCalles = Grupo(raiz, "Calles y Senderos");
            Transform gAgua = Grupo(raiz, "Estero");
            Transform gAccesos = Grupo(raiz, "Accesos");
            Transform gMonumentos = Grupo(raiz, "Monumentos");

            // Suelo general (pasto)
            Losa(gSuelo, "Terreno", new Vector3(40f, 0f, 20f), new Vector2(1000f, 1000f), 0f, 0.2f, -0.2f, "suelo", true);

            foreach (var e in CampusData.Edificios)
                CrearEdificio(e.Tipo == TipoLugar.Servicio ? gBanos : gBloques, e);
            foreach (var a in CampusData.Arcos) CrearArco(gBloques, a);

            foreach (var a in CampusData.Areas)
            {
                Transform g = a.Tipo == TipoLugar.Estacionamiento ? gParqueos
                            : a.Tipo == TipoLugar.AreaVerde ? gVerdes : gDeportes;
                CrearArea(g, a);
            }
            CrearEstadio(gDeportes, CampusData.Estadio);

            foreach (var c in CampusData.Calles)
                CrearLinea(gCalles, c, c.Estilo == "sendero" || c.Estilo == "peatonal" ? 0.12f : 0.10f);
            CrearLinea(gAgua, CampusData.Estero, 0.07f);

            foreach (var p in CampusData.Entradas) CrearAcceso(gAccesos, p);
            CrearMonumento(gMonumentos, CampusData.Monumento);

            CrearAulaK301(raiz.transform);
            PrepararCamaraYLuz();
            CrearRecorrido(raiz.transform);

            Selection.activeGameObject = raiz;
            GuardarEscena(raiz.scene);
            AssetDatabase.SaveAssets();
            Debug.Log("[UNEMI] Campus generado: " + (CampusData.Edificios.Length + CampusData.Arcos.Length) +
                      " edificios, " + CampusData.Areas.Length + " áreas, " + CampusData.Entradas.Length +
                      " accesos. Dale Play para ver a la personita caminar.");
        }

        /// <summary>Guarda la escena en Assets/UNEMI/Escenas y la agrega a la lista de Build.</summary>
        static void GuardarEscena(UnityEngine.SceneManagement.Scene escena)
        {
            EditorSceneManager.MarkSceneDirty(escena);
            if (string.IsNullOrEmpty(escena.path))
            {
                CrearCarpeta(CarpetaEscenas);
                EditorSceneManager.SaveScene(escena, CarpetaEscenas + "/CampusUNEMI.unity");
            }
            else EditorSceneManager.SaveScene(escena);

            var lista = new List<EditorBuildSettingsScene>(EditorBuildSettings.scenes);
            if (!lista.Exists(s => s.path == escena.path))
            {
                lista.Insert(0, new EditorBuildSettingsScene(escena.path, true));
                EditorBuildSettings.scenes = lista.ToArray();
            }
        }

        [MenuItem("UNEMI/Exportar lugares a JSON", priority = 20)]
        public static void ExportarJson()
        {
#if UNITY_2023_1_OR_NEWER
            var lugares = Object.FindObjectsByType<CampusLocation>(FindObjectsSortMode.None);
            var geo = Object.FindFirstObjectByType<CampusGeoReference>();
#else
            var lugares = Object.FindObjectsOfType<CampusLocation>();
            var geo = Object.FindObjectOfType<CampusGeoReference>();
#endif
            if (lugares.Length == 0)
            {
                EditorUtility.DisplayDialog("Campus UNEMI", "Primero genera el campus (UNEMI > Generar Campus 3D).", "OK");
                return;
            }
            bool conGps = geo != null && geo.TieneCoordenadas && geo.Calibrar();

            var lista = new ListaLugares();
            foreach (var l in lugares)
            {
                var d = new LugarJson { id = l.id, nombre = l.nombre, tipo = l.tipo.ToString() };
                Vector3 p = l.PosicionDestino;
                d.x = p.x; d.z = p.z;
                if (conGps) geo.UnityAGps(p, out d.latitud, out d.longitud);
                lista.lugares.Add(d);
            }
            lista.lugares.Sort((a, b) => string.CompareOrdinal(a.id, b.id));
            string ruta = "Assets/UNEMI/lugares_campus.json";
            File.WriteAllText(ruta, JsonUtility.ToJson(lista, true));
            AssetDatabase.Refresh();
            Debug.Log("[UNEMI] Exportados " + lista.lugares.Count + " lugares a " + ruta +
                      (conGps ? " (con GPS)" : " (sin GPS: calibra CampusGeoReference)"));
        }

        [System.Serializable] class LugarJson { public string id, nombre, tipo; public float x, z; public double latitud, longitud; }
        [System.Serializable] class ListaLugares { public List<LugarJson> lugares = new List<LugarJson>(); }

        // ------------------------------------------------------------------ Edificios

        static void CrearEdificio(Transform padre, EdificioDef e)
        {
            string nombreObj = string.IsNullOrEmpty(e.Nombre) ? "Edificio (" + e.Id + ")" : e.Nombre + (e.Tipo == TipoLugar.Servicio ? " (" + e.Id + ")" : "");
            var go = new GameObject(nombreObj);
            go.transform.SetParent(padre, false);
            go.transform.localPosition = new Vector3(e.X, 0f, e.Z);
            go.transform.localRotation = Quaternion.Euler(0f, e.Rot, 0f);
            Lugar(go, e.Id, string.IsNullOrEmpty(e.Nombre) ? nombreObj : e.Nombre, e.Tipo);

            Caja(go.transform, "Volumen", new Vector3(0f, e.Alto * 0.5f, 0f), new Vector3(e.Ancho, e.Alto, e.Largo), 0f, MatColor(e.Estilo), true);
            Caja(go.transform, "Techo", new Vector3(0f, e.Alto + 0.15f, 0f), new Vector3(e.Ancho * 0.92f, 0.3f, e.Largo * 0.92f), 0f,
                 MatColor(e.Estilo, 0.72f), false);

            if (!string.IsNullOrEmpty(e.Nombre))
            {
                float letra = e.Tipo == TipoLugar.Servicio ? AlturaLetraBloque * 0.7f : AlturaLetraBloque;
                Etiqueta(go.transform, e.Nombre, new Vector3(0f, e.Alto + 4f, 0f), letra);
            }
        }

        static void CrearArco(Transform padre, ArcoDef a)
        {
            Vector2 c = a.CentroBloque;
            var go = new GameObject(a.Nombre);
            go.transform.SetParent(padre, false);
            go.transform.localPosition = new Vector3(c.x, 0f, c.y);
            Lugar(go, a.Id, a.Nombre, TipoLugar.Bloque);

            Material pared = MatColor(a.Estilo), techo = MatColor(a.Estilo, 0.72f);
            const int segmentos = 10;
            float paso = (a.AnguloFin - a.AnguloInicio) / segmentos;
            float grosor = a.RadioExterior - a.RadioInterior;
            for (int i = 0; i < segmentos; i++)
            {
                float am = a.AnguloInicio + paso * (i + 0.5f);
                float rad = am * Mathf.Deg2Rad;
                float largo = 2f * a.RadioExterior * Mathf.Sin(Mathf.Abs(paso) * 0.5f * Mathf.Deg2Rad) * 1.02f;
                Vector3 centroMundo = new Vector3(a.CX + a.RadioMedio * Mathf.Cos(rad), 0f, a.CZ + a.RadioMedio * Mathf.Sin(rad));
                Vector3 local = centroMundo - go.transform.localPosition;
                float rotY = -90f - am; // eje X local tangente al arco
                Caja(go.transform, "Segmento " + (i + 1), new Vector3(local.x, a.Alto * 0.5f, local.z),
                     new Vector3(largo, a.Alto, grosor), rotY, pared, true);
                Caja(go.transform, "Techo " + (i + 1), new Vector3(local.x, a.Alto + 0.15f, local.z),
                     new Vector3(largo, 0.3f, grosor * 0.9f), rotY, techo, false);
            }
            Etiqueta(go.transform, a.Nombre, new Vector3(0f, a.Alto + 4f, 0f), AlturaLetraBloque);
        }

        // ------------------------------------------------------------------ Áreas

        static void CrearArea(Transform padre, AreaDef a)
        {
            string nombreObj = string.IsNullOrEmpty(a.Nombre) ? a.Id : a.Nombre;
            if (a.Id.StartsWith("VERDE")) nombreObj += " " + a.Id.Substring(5);
            var go = new GameObject(nombreObj);
            go.transform.SetParent(padre, false);
            go.transform.localPosition = new Vector3(a.X, 0f, a.Z);
            go.transform.localRotation = Quaternion.Euler(0f, a.Rot, 0f);
            Lugar(go, a.Id, string.IsNullOrEmpty(a.Nombre) ? a.Id : a.Nombre, a.Tipo);

            float alto = a.Estilo == "agua" ? 0.18f : a.Estilo == "cancha" ? 0.12f : 0.06f;
            Losa(go.transform, "Superficie", Vector3.zero, new Vector2(a.Ancho, a.Largo), 0f, alto, 0f, a.Estilo, true);

            if (a.Estilo == "parqueo")
            {
                int filas = Mathf.Max(2, Mathf.RoundToInt(a.Largo / 14f));
                for (int i = 0; i < filas; i++)
                {
                    float z = -a.Largo * 0.5f + (i + 0.5f) * a.Largo / filas;
                    Losa(go.transform, "Linea " + (i + 1), new Vector3(0f, 0f, z), new Vector2(a.Ancho * 0.85f, 0.4f), 0f, 0.02f, alto, "linea", false);
                }
            }
            if (a.Estilo == "verde")
            {
                var rnd = new System.Random(a.Id.GetHashCode());
                int arboles = Mathf.Clamp(Mathf.RoundToInt(a.Ancho * a.Largo / 600f), 4, 40);
                for (int i = 0; i < arboles; i++)
                {
                    float x = (float)(rnd.NextDouble() - 0.5) * a.Ancho * 0.85f;
                    float z = (float)(rnd.NextDouble() - 0.5) * a.Largo * 0.85f;
                    Arbol(go.transform, new Vector3(x, alto, z));
                }
            }

            if (!string.IsNullOrEmpty(a.Nombre))
                Etiqueta(go.transform, a.Nombre, new Vector3(0f, 3f, 0f), a.Estilo == "cancha" ? AlturaLetraBloque : AlturaLetraArea);
        }

        static void CrearEstadio(Transform padre, AreaDef e)
        {
            var go = new GameObject(e.Nombre);
            go.transform.SetParent(padre, false);
            go.transform.localPosition = new Vector3(e.X, 0f, e.Z);
            go.transform.localRotation = Quaternion.Euler(0f, e.Rot, 0f);
            Lugar(go, e.Id, e.Nombre, TipoLugar.Deportivo);

            Elipse(go.transform, "Pista", new Vector3(0f, 0.08f, 0f), e.Ancho, e.Largo, 0.16f, "pista");
            Elipse(go.transform, "Cancha", new Vector3(0f, 0.12f, 0f), e.Ancho * 0.68f, e.Largo * 0.8f, 0.24f, "campo");
            Caja(go.transform, "Graderio", new Vector3(-e.Ancho * 0.5f + 6f, 4f, 0f), new Vector3(9f, 8f, e.Largo * 0.42f), 0f, Mat("graderio"), true);

            Etiqueta(go.transform, e.Nombre, new Vector3(0f, 10f, 0f), AlturaLetraArea);
        }

        static void CrearLinea(Transform padre, LineaDef l, float alto)
        {
            string nombre = !string.IsNullOrEmpty(l.Nombre) ? l.Nombre
                          : l.Estilo == "sendero" ? "Sendero"
                          : l.Estilo == "peatonal" ? "Paseo peatonal" : "Calle";
            var go = new GameObject(nombre);
            go.transform.SetParent(padre, false);
            var p = l.Puntos;
            for (int i = 0; i < p.Length - 1; i++)
            {
                Vector2 a = p[i], b = p[i + 1];
                Vector2 d = b - a;
                float largo = d.magnitude;
                if (largo < 0.01f) continue;
                float rotY = Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg;
                Vector2 m = (a + b) * 0.5f;
                Losa(go.transform, "Tramo " + (i + 1), new Vector3(m.x, 0f, m.y), new Vector2(l.Ancho, largo + l.Ancho), rotY, alto, 0f, l.Estilo, true);
            }

            if (!string.IsNullOrEmpty(l.Nombre))
            {
                int mejor = 0; float max = 0f;
                for (int i = 0; i < p.Length - 1; i++) { float d = (p[i + 1] - p[i]).magnitude; if (d > max) { max = d; mejor = i; } }
                Vector2 m = Vector2.Lerp(p[mejor], p[mejor + 1], l.Estilo == "estero" ? 0.55f : 0.45f);
                Etiqueta(go.transform, l.Nombre, new Vector3(m.x, 3f, m.y), AlturaLetraArea);
            }
        }

        // ------------------------------------------------------------------ Accesos, monumento, aula

        static void CrearAcceso(Transform padre, PuntoDef p)
        {
            var go = new GameObject(p.Nombre);
            go.transform.SetParent(padre, false);
            go.transform.localPosition = new Vector3(p.X, 0f, p.Z);
            var loc = Lugar(go, p.Id, p.Nombre, p.Tipo);
            loc.puntoAcceso = go.transform;

            string estilo = p.Tipo == TipoLugar.EntradaVehicular ? "entrada_veh"
                          : p.Tipo == TipoLugar.SalidaVehicular ? "salida_veh" : "entrada";
            Elipse(go.transform, "Base", new Vector3(0f, 0.15f, 0f), 6f, 6f, 0.3f, estilo);
            Cilindro(go.transform, "Poste", new Vector3(0f, 2f, 0f), new Vector3(0.8f, 2f, 0.8f), estilo);
            if (p.Tipo != TipoLugar.Entrada)
            {
                // Pluma de la garita para los accesos vehiculares
                Caja(go.transform, "Pluma", new Vector3(3.5f, 2.8f, 0f), new Vector3(7f, 0.35f, 0.35f), 0f, Mat("blanco"), false);
                Caja(go.transform, "Pluma franja", new Vector3(3.5f, 2.8f, 0f), new Vector3(1.2f, 0.4f, 0.4f), 0f, Mat(estilo), false);
            }
            Etiqueta(go.transform, p.Nombre, new Vector3(0f, 8f, 0f), AlturaLetraBloque * 0.8f);
        }

        static void CrearMonumento(Transform padre, PuntoDef p)
        {
            var go = new GameObject(p.Nombre);
            go.transform.SetParent(padre, false);
            go.transform.localPosition = new Vector3(p.X, 0f, p.Z);
            var loc = Lugar(go, p.Id, p.Nombre, TipoLugar.Monumento);
            loc.puntoAcceso = go.transform;

            Elipse(go.transform, "Plaza", new Vector3(0f, 0.1f, 0f), 14f, 14f, 0.2f, "monumento");
            Caja(go.transform, "Pedestal", new Vector3(0f, 0.95f, 0f), new Vector3(9f, 1.5f, 2.5f), 0f, Mat("monumento"), true);

            // Tres astas: Guayas, Ecuador (centro, más alta) y UNEMI
            Asta(go.transform, new Vector3(-3.2f, 1.7f, 0f), 10f, new[] { "celeste", "blanco", "celeste", "blanco", "celeste" }, new[] { 1f, 1f, 1f, 1f, 1f });
            Asta(go.transform, new Vector3(0f, 1.7f, 0f), 12f, new[] { "ec_amarillo", "ec_azul", "ec_rojo" }, new[] { 2f, 1f, 1f });
            Asta(go.transform, new Vector3(3.2f, 1.7f, 0f), 10f, new[] { "ec_azul", "blanco" }, new[] { 2f, 1f });

            Etiqueta(go.transform, p.Nombre, new Vector3(0f, 17f, 0f), AlturaLetraBloque * 0.8f);
        }

        static void Asta(Transform padre, Vector3 basePos, float alto, string[] franjas, float[] pesos)
        {
            Cilindro(padre, "Asta", basePos + new Vector3(0f, alto * 0.5f, 0f), new Vector3(0.18f, alto * 0.5f, 0.18f), "asta");
            const float ancho = 2.4f, altoBandera = 1.6f;
            float total = 0f; foreach (var w in pesos) total += w;
            float y = basePos.y + alto - 0.1f;
            for (int i = 0; i < franjas.Length; i++)
            {
                float h = altoBandera * pesos[i] / total;
                Caja(padre, "Bandera", new Vector3(basePos.x + 0.1f + ancho * 0.5f, y - h * 0.5f, basePos.z),
                     new Vector3(ancho, h, 0.05f), 0f, Mat(franjas[i]), false);
                y -= h;
            }
        }

        static void CrearAulaK301(Transform raiz)
        {
            var bloqueK = raiz.Find("Bloques/Bloque K");
            if (bloqueK == null) return;

            var aula = new GameObject("Aula K-301");
            aula.transform.SetParent(bloqueK, false);
            aula.transform.localPosition = new Vector3(0f, 7.5f, 0f); // tercer piso aprox.
            Lugar(aula, "K-301", "Aula K-301 (Bloque K)", TipoLugar.Aula);

            var pin = new GameObject("Pin");
            pin.transform.SetParent(aula.transform, false);
            pin.transform.localPosition = new Vector3(0f, 14f, 0f);
            Cilindro(pin.transform, "Palo", Vector3.zero, new Vector3(0.6f, 4f, 0.6f), "destacado");
            var bola = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            bola.name = "Cabeza"; bola.transform.SetParent(pin.transform, false);
            bola.transform.localPosition = new Vector3(0f, 5f, 0f);
            bola.transform.localScale = Vector3.one * 5f;
            bola.GetComponent<Renderer>().sharedMaterial = Mat("destacado");
            Object.DestroyImmediate(bola.GetComponent<Collider>());
        }

        // ------------------------------------------------------------------ Personita y recorrido

        /// <summary>
        /// Crea la personita, la línea de la ruta, la meta y el objeto "RouteAnimator"
        /// (el nombre que usa la web para enviar la ruta), y los conecta con la cámara.
        /// </summary>
        static void CrearRecorrido(Transform raiz)
        {
            Vector3 inicio = Vector3.zero;
            foreach (var p in CampusData.Entradas)
                if (p.Id == "ENTRADA_PEATONAL") inicio = new Vector3(p.X, 0f, p.Z);

            PersonaCaminante persona = CrearPersonita(raiz, inicio);

            // Línea amarilla que dibuja el camino
            var goLinea = new GameObject("Linea de la ruta");
            goLinea.transform.SetParent(raiz, false);
            var linea = goLinea.AddComponent<LineRenderer>();
            linea.useWorldSpace = true;
            linea.positionCount = 0;
            linea.widthMultiplier = 2.2f;
            linea.numCornerVertices = 4;
            linea.numCapVertices = 4;
            linea.shadowCastingMode = ShadowCastingMode.Off;
            linea.sharedMaterial = ObtenerMaterial("UNEMI_ruta", Hex(Estilos["ruta"]), true);

            // Meta: aro rojo con un poste en el punto de llegada
            var meta = new GameObject("Meta");
            meta.transform.SetParent(raiz, false);
            Elipse(meta.transform, "Aro", new Vector3(0f, 0.1f, 0f), 5f, 5f, 0.2f, "meta");
            Cilindro(meta.transform, "Poste", new Vector3(0f, 3f, 0f), new Vector3(0.35f, 3f, 0.35f), "meta");
            NoEstatico(meta);
            meta.SetActive(false);

            // Objeto que recibe la ruta de la web / Django
            var goRuta = new GameObject("RouteAnimator");
            goRuta.transform.SetParent(raiz, false);
            var ruta = goRuta.AddComponent<RutaCampus>();
            goRuta.AddComponent<ApiClient>();
            ruta.persona = persona;
            ruta.linea = linea;
            ruta.meta = meta.transform;

            // La cámara sigue a la personita
            var cam = Camera.main;
            var ctrl = cam != null ? cam.GetComponent<CampusCameraController>() : null;
            if (ctrl != null)
            {
                Undo.RecordObject(ctrl, "Camara campus");
                ctrl.objetivo = persona.transform;
                ruta.camara = ctrl;
                persona.camara = ctrl;
            }
        }

        static PersonaCaminante CrearPersonita(Transform raiz, Vector3 posicion)
        {
            var go = new GameObject("Personita");
            go.transform.SetParent(raiz, false);
            go.transform.localPosition = posicion;

            var cc = go.AddComponent<CharacterController>();
            cc.height = 1.8f;
            cc.radius = 0.35f;
            cc.center = new Vector3(0f, 0.9f, 0f);
            cc.stepOffset = 0.4f;

            // "Cuerpo" rebota un poco al caminar; las extremidades giran desde la cadera / hombro
            var cuerpo = new GameObject("Cuerpo").transform;
            cuerpo.SetParent(go.transform, false);

            Transform piernaIzq = Articulacion(cuerpo, "Pierna izquierda", new Vector3(-0.12f, 0.85f, 0f));
            Transform piernaDer = Articulacion(cuerpo, "Pierna derecha", new Vector3(0.12f, 0.85f, 0f));
            foreach (var pierna in new[] { piernaIzq, piernaDer })
            {
                Caja(pierna, "Pierna", new Vector3(0f, -0.42f, 0f), new Vector3(0.18f, 0.85f, 0.2f), 0f, Mat("pantalon"), false);
                Caja(pierna, "Zapato", new Vector3(0f, -0.81f, 0.05f), new Vector3(0.2f, 0.1f, 0.3f), 0f, Mat("zapato"), false);
            }

            Caja(cuerpo, "Torso", new Vector3(0f, 1.2f, 0f), new Vector3(0.5f, 0.7f, 0.28f), 0f, Mat("camisa"), false);
            Caja(cuerpo, "Mochila", new Vector3(0f, 1.22f, -0.21f), new Vector3(0.4f, 0.5f, 0.15f), 0f, Mat("mochila"), false);
            Esfera(cuerpo, "Cabeza", new Vector3(0f, 1.74f, 0f), new Vector3(0.34f, 0.36f, 0.34f), "piel");
            Esfera(cuerpo, "Cabello", new Vector3(0f, 1.82f, -0.02f), new Vector3(0.36f, 0.22f, 0.36f), "cabello");

            Transform brazoIzq = Articulacion(cuerpo, "Brazo izquierdo", new Vector3(-0.32f, 1.5f, 0f));
            Transform brazoDer = Articulacion(cuerpo, "Brazo derecho", new Vector3(0.32f, 1.5f, 0f));
            foreach (var brazo in new[] { brazoIzq, brazoDer })
            {
                Caja(brazo, "Brazo", new Vector3(0f, -0.3f, 0f), new Vector3(0.13f, 0.62f, 0.15f), 0f, Mat("camisa"), false);
                Esfera(brazo, "Mano", new Vector3(0f, -0.66f, 0f), Vector3.one * 0.13f, "piel");
            }

            // Aro amarillo en el piso y cartel "Tú" para verla desde lejos
            Elipse(go.transform, "Aro", new Vector3(0f, 0.05f, 0f), 1.6f, 1.6f, 0.04f, "ruta");
            Etiqueta(go.transform, "Tú", new Vector3(0f, 3.4f, 0f), AlturaLetraBloque);

            NoEstatico(go);   // se mueve: no puede ser estática

            var persona = go.AddComponent<PersonaCaminante>();
            persona.cuerpo = cuerpo;
            persona.piernaIzquierda = piernaIzq;
            persona.piernaDerecha = piernaDer;
            persona.brazoIzquierdo = brazoIzq;
            persona.brazoDerecho = brazoDer;
            return persona;
        }

        static Transform Articulacion(Transform padre, string nombre, Vector3 posLocal)
        {
            var t = new GameObject(nombre).transform;
            t.SetParent(padre, false);
            t.localPosition = posLocal;
            return t;
        }

        static void Esfera(Transform padre, string nombre, Vector3 posLocal, Vector3 escala, string estilo)
        {
            var e = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            e.name = nombre;
            e.transform.SetParent(padre, false);
            e.transform.localPosition = posLocal;
            e.transform.localScale = escala;
            e.GetComponent<Renderer>().sharedMaterial = Mat(estilo);
            Object.DestroyImmediate(e.GetComponent<Collider>());
        }

        static void NoEstatico(GameObject go)
        {
            foreach (var t in go.GetComponentsInChildren<Transform>(true)) t.gameObject.isStatic = false;
        }

        // ------------------------------------------------------------------ Piezas básicas

        static CampusLocation Lugar(GameObject go, string id, string nombre, TipoLugar tipo)
        {
            var l = go.AddComponent<CampusLocation>();
            l.id = id; l.nombre = nombre; l.tipo = tipo;
            return l;
        }

        static Transform Grupo(GameObject raiz, string nombre)
        {
            var g = new GameObject(nombre);
            g.transform.SetParent(raiz.transform, false);
            return g.transform;
        }

        static GameObject Caja(Transform padre, string nombre, Vector3 posLocal, Vector3 tamano, float rotY, Material mat, bool colision)
        {
            var c = GameObject.CreatePrimitive(PrimitiveType.Cube);
            c.name = nombre;
            c.transform.SetParent(padre, false);
            c.transform.localPosition = posLocal;
            c.transform.localRotation = Quaternion.Euler(0f, rotY, 0f);
            c.transform.localScale = tamano;
            c.GetComponent<Renderer>().sharedMaterial = mat;
            if (!colision) Object.DestroyImmediate(c.GetComponent<Collider>());
            c.isStatic = true;
            return c;
        }

        /// <summary>Placa plana: su cara inferior queda en baseY y la superior en baseY + grosor.</summary>
        static GameObject Losa(Transform padre, string nombre, Vector3 centro, Vector2 tamano, float rotY, float grosor, float baseY, string estilo, bool colision)
        {
            return Caja(padre, nombre, new Vector3(centro.x, baseY + grosor * 0.5f, centro.z),
                        new Vector3(tamano.x, grosor, tamano.y), rotY, Mat(estilo), colision);
        }

        static void Elipse(Transform padre, string nombre, Vector3 posLocal, float ancho, float largo, float grosor, string estilo)
        {
            // El cilindro de Unity mide 2 de alto y 1 de diámetro
            Cilindro(padre, nombre, posLocal, new Vector3(ancho, grosor * 0.5f, largo), estilo);
        }

        static void Cilindro(Transform padre, string nombre, Vector3 posLocal, Vector3 escala, string estilo)
        {
            var c = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            c.name = nombre;
            c.transform.SetParent(padre, false);
            c.transform.localPosition = posLocal;
            c.transform.localScale = escala;
            c.GetComponent<Renderer>().sharedMaterial = Mat(estilo);
            Object.DestroyImmediate(c.GetComponent<Collider>());
            c.isStatic = true;
        }

        static void Arbol(Transform padre, Vector3 pos)
        {
            Cilindro(padre, "Tronco", pos + new Vector3(0f, 1.5f, 0f), new Vector3(0.6f, 1.5f, 0.6f), "tronco");
            var copa = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            copa.name = "Copa"; copa.transform.SetParent(padre, false);
            copa.transform.localPosition = pos + new Vector3(0f, 4.5f, 0f);
            copa.transform.localScale = Vector3.one * 4.5f;
            copa.GetComponent<Renderer>().sharedMaterial = Mat("arbol");
            Object.DestroyImmediate(copa.GetComponent<Collider>());
        }

        /// <summary>Cartel blanco con el nombre (como en el recorrido 3D de referencia).</summary>
        static void Etiqueta(Transform padre, string texto, Vector3 posLocal, float alturaLetra)
        {
            var go = new GameObject("Nombre");
            go.transform.SetParent(padre, false);
            go.transform.localPosition = posLocal;
            go.transform.rotation = Quaternion.Euler(90f, 0f, 0f); // en el editor: legible desde arriba

            var txt = new GameObject("Texto");
            txt.transform.SetParent(go.transform, false);
            var tm = txt.AddComponent<TextMesh>();
            tm.text = texto;
            tm.anchor = TextAnchor.MiddleCenter;
            tm.alignment = TextAlignment.Center;
            tm.fontSize = TamanoFuente;
            tm.characterSize = alturaLetra / (0.1f * TamanoFuente);
            tm.color = ColorTexto;
            tm.fontStyle = FontStyle.Bold;
            if (fuente != null)
            {
                tm.font = fuente;
                txt.GetComponent<MeshRenderer>().sharedMaterial = fuente.material;
            }

            // Fondo blanco detrás del texto (el tamaño final lo ajusta LabelBillboard)
            var fondo = GameObject.CreatePrimitive(PrimitiveType.Quad);
            fondo.name = "Fondo";
            fondo.transform.SetParent(go.transform, false);
            fondo.transform.localPosition = new Vector3(0f, 0f, alturaLetra * 0.08f);
            fondo.transform.localScale = new Vector3(texto.Length * alturaLetra * 0.6f + alturaLetra, alturaLetra * 1.6f, 1f);
            fondo.GetComponent<Renderer>().sharedMaterial = MatPlaca();
            Object.DestroyImmediate(fondo.GetComponent<Collider>());

            var bb = go.AddComponent<LabelBillboard>();
            bb.texto = tm;
            bb.fondo = fondo.transform;
            bb.margen = alturaLetra * 0.45f;
        }

        // ------------------------------------------------------------------ Materiales

        static Material Mat(string estilo)
        {
            string hex;
            if (!Estilos.TryGetValue(estilo, out hex)) hex = "CCCCCC";
            return ObtenerMaterial("UNEMI_" + estilo, Hex(hex), false);
        }

        /// <summary>Material de un color "#RRGGBB"; factor menor que 1 lo oscurece (techos).</summary>
        static Material MatColor(string hex, float factor = 1f)
        {
            if (string.IsNullOrEmpty(hex) || !hex.StartsWith("#")) return Mat(hex ?? "techo");
            Color c = Hex(hex.Substring(1));
            string nombre = "UNEMI_" + hex.Substring(1);
            if (factor < 1f)
            {
                c = new Color(c.r * factor, c.g * factor, c.b * factor, 1f);
                nombre += "_techo";
            }
            return ObtenerMaterial(nombre, c, false);
        }

        static Material MatPlaca()
        {
            return ObtenerMaterial("UNEMI_placa_etiqueta", UnityEngine.Color.white, true);
        }

        static Material ObtenerMaterial(string nombre, Color color, bool unlit)
        {
            if (cache == null) cache = new Dictionary<string, Material>();
            Material m;
            if (cache.TryGetValue(nombre, out m) && m != null) return m;

            CrearCarpeta(CarpetaMateriales);
            string ruta = CarpetaMateriales + "/" + nombre + ".mat";
            Shader shader = unlit ? shaderUnlit : shaderLit;
            m = AssetDatabase.LoadAssetAtPath<Material>(ruta);
            if (m == null)
            {
                m = new Material(shader);
                AssetDatabase.CreateAsset(m, ruta);
            }
            else if (m.shader != shader) m.shader = shader;

            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", color);
            if (m.HasProperty("_Color")) m.SetColor("_Color", color);
            if (m.HasProperty("_UnlitColor")) m.SetColor("_UnlitColor", color);
            if (m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", 0.1f);
            if (m.HasProperty("_Glossiness")) m.SetFloat("_Glossiness", 0.1f);
            EditorUtility.SetDirty(m);
            cache[nombre] = m;
            return m;
        }

        static void PrepararShaders()
        {
            cache = new Dictionary<string, Material>();
            var rp = GraphicsSettings.currentRenderPipeline;
            string tipo = rp == null ? "" : rp.GetType().Name;
            if (tipo.Contains("Universal"))
            {
                shaderLit = Primero("Universal Render Pipeline/Lit", "Universal Render Pipeline/Simple Lit");
                shaderUnlit = Primero("Universal Render Pipeline/Unlit");
            }
            else if (tipo.Contains("HD"))
            {
                shaderLit = Primero("HDRP/Lit");
                shaderUnlit = Primero("HDRP/Unlit");
            }
            else
            {
                shaderLit = Primero("Standard");
                shaderUnlit = Primero("Unlit/Color");
            }
            if (shaderLit == null) shaderLit = Primero("Standard", "Diffuse");
            if (shaderUnlit == null) shaderUnlit = shaderLit;
        }

        static Shader Primero(params string[] nombres)
        {
            foreach (var n in nombres)
            {
                var s = Shader.Find(n);
                if (s != null) return s;
            }
            return null;
        }

        static Font CargarFuente()
        {
#if UNITY_2022_2_OR_NEWER
            return Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
#else
            return Resources.GetBuiltinResource<Font>("Arial.ttf");
#endif
        }

        // ------------------------------------------------------------------ Cámara y luz

        static void PrepararCamaraYLuz()
        {
            var cam = Camera.main;
            if (cam == null)
            {
                var go = new GameObject("Main Camera");
                go.tag = "MainCamera";
                cam = go.AddComponent<Camera>();
                Undo.RegisterCreatedObjectUndo(go, "Camara campus");
            }
            Undo.RecordObject(cam, "Camara campus");
            cam.farClipPlane = 3000f;
            cam.nearClipPlane = 0.5f;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = ColorCielo;
            if (cam.GetComponent<CampusCameraController>() == null)
                Undo.AddComponent<CampusCameraController>(cam.gameObject);
            var ctrl = cam.GetComponent<CampusCameraController>();
            Quaternion r = Quaternion.Euler(ctrl.inclinacion, ctrl.giro, 0f);
            cam.transform.SetPositionAndRotation(ctrl.foco - r * Vector3.forward * ctrl.distancia, r);

            bool hayLuz = false;
#if UNITY_2023_1_OR_NEWER
            var luces = Object.FindObjectsByType<Light>(FindObjectsSortMode.None);
#else
            var luces = Object.FindObjectsOfType<Light>();
#endif
            foreach (var l in luces)
                if (l.type == LightType.Directional) { hayLuz = true; break; }
            if (!hayLuz)
            {
                var luz = new GameObject("Sol");
                var l = luz.AddComponent<Light>();
                l.type = LightType.Directional;
                l.intensity = 1.1f;
                luz.transform.rotation = Quaternion.Euler(55f, -30f, 0f);
                Undo.RegisterCreatedObjectUndo(luz, "Luz campus");
            }
        }

        // ------------------------------------------------------------------ Utilidades

        static void CrearCarpeta(string ruta)
        {
            if (AssetDatabase.IsValidFolder(ruta)) return;
            string padre = Path.GetDirectoryName(ruta).Replace('\\', '/');
            CrearCarpeta(padre);
            AssetDatabase.CreateFolder(padre, Path.GetFileName(ruta));
        }

        static Color Hex(string h)
        {
            Color c;
            ColorUtility.TryParseHtmlString("#" + h.TrimStart('#'), out c);
            return c;
        }
    }
}
