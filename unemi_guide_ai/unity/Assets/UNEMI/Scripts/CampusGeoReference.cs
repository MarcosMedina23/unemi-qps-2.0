using UnityEngine;

namespace UNEMI.Campus
{
    /// <summary>
    /// Convierte coordenadas GPS reales (latitud, longitud) a posiciones del campus en Unity y al revés.
    ///
    /// CÓMO CALIBRAR (una sola vez):
    ///  1. Abre Google Maps, haz clic derecho sobre el centro del Bloque K y copia las coordenadas.
    ///  2. Pega la latitud y longitud en "Punto A".
    ///  3. Haz lo mismo con el centro del Estadio en "Punto B" (dos puntos lejanos dan mejor precisión).
    /// Con eso el script corrige solo la escala y la rotación del modelo.
    /// </summary>
    public class CampusGeoReference : MonoBehaviour
    {
        [Header("Punto A (lugar del campus + su coordenada real)")]
        public string idLugarA = "K";
        public double latitudA;
        public double longitudA;

        [Header("Punto B (lugar del campus + su coordenada real)")]
        public string idLugarB = "ESTADIO";
        public double latitudB;
        public double longitudB;

        const double MetrosPorGradoLat = 110574.0;
        const double MetrosPorGradoLonEcuador = 111320.0;

        bool calibrado;
        Vector2 unityA;
        float escala = 1f;   // metros Unity por metro real
        float angulo;        // radianes

        public bool TieneCoordenadas =>
            latitudA != 0 && longitudA != 0 && latitudB != 0 && longitudB != 0;

        void Awake()
        {
            Calibrar();
        }

        /// <summary>Recalcula escala y rotación. Llamar si cambias los puntos en tiempo de ejecución.</summary>
        public bool Calibrar()
        {
            calibrado = false;
            if (!TieneCoordenadas)
            {
                Debug.LogWarning("[CampusGeoReference] Faltan las coordenadas reales de los puntos A y B.");
                return false;
            }
            var a = CampusLocation.Buscar(idLugarA);
            var b = CampusLocation.Buscar(idLugarB);
            if (a == null || b == null)
            {
                Debug.LogWarning("[CampusGeoReference] No se encontraron los lugares '" + idLugarA + "' o '" + idLugarB + "'.");
                return false;
            }

            unityA = new Vector2(a.transform.position.x, a.transform.position.z);
            Vector2 unityB = new Vector2(b.transform.position.x, b.transform.position.z);
            Vector2 realAB = AMetros(latitudB, longitudB);
            Vector2 unityAB = unityB - unityA;

            if (realAB.sqrMagnitude < 1f) return false;
            escala = unityAB.magnitude / realAB.magnitude;
            angulo = Mathf.Atan2(unityAB.y, unityAB.x) - Mathf.Atan2(realAB.y, realAB.x);
            calibrado = true;
            return true;
        }

        /// <summary>GPS → posición en Unity (y = 0).</summary>
        public Vector3 GpsAUnity(double latitud, double longitud)
        {
            if (!calibrado && !Calibrar()) return Vector3.zero;
            Vector2 v = Rotar(AMetros(latitud, longitud), angulo) * escala + unityA;
            return new Vector3(v.x, 0f, v.y);
        }

        /// <summary>Posición en Unity → GPS.</summary>
        public void UnityAGps(Vector3 posicion, out double latitud, out double longitud)
        {
            latitud = 0; longitud = 0;
            if (!calibrado && !Calibrar()) return;
            Vector2 v = new Vector2(posicion.x, posicion.z) - unityA;
            v = Rotar(v / escala, -angulo);
            latitud = latitudA + v.y / MetrosPorGradoLat;
            longitud = longitudA + v.x / (MetrosPorGradoLonEcuador * System.Math.Cos(latitudA * System.Math.PI / 180.0));
        }

        /// <summary>Metros (Este, Norte) desde el punto A.</summary>
        Vector2 AMetros(double lat, double lon)
        {
            double este = (lon - longitudA) * MetrosPorGradoLonEcuador * System.Math.Cos(latitudA * System.Math.PI / 180.0);
            double norte = (lat - latitudA) * MetrosPorGradoLat;
            return new Vector2((float)este, (float)norte);
        }

        static Vector2 Rotar(Vector2 v, float rad)
        {
            float c = Mathf.Cos(rad), s = Mathf.Sin(rad);
            return new Vector2(v.x * c - v.y * s, v.x * s + v.y * c);
        }
    }
}
