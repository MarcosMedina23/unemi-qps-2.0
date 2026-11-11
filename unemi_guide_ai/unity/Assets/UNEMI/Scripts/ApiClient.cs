// Consume la API de rutas de UNEMI Guide AI (POST /api/rutas/calcular/).
//
// Autenticación (la API usa la sesión de Django):
//   - Unity WebGL dentro de la página web: el navegador envía la cookie de
//     sesión solo. Solo falta el token CSRF: la página lo pasa con
//     unityInstance.SendMessage("RouteAnimator", "SetCsrfToken", token).
//   - Unity en el editor o en una app de escritorio: copia en el Inspector
//     los valores de las cookies "sessionid" y "csrftoken" del navegador
//     (F12 > Aplicación > Cookies) después de iniciar sesión en la web.

using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

namespace UNEMI.Campus
{
    // -----------------------------------------------------------------------
    // Clases de datos: mismos nombres de campos que el JSON de la API.
    // -----------------------------------------------------------------------
    [Serializable]
    public class PuntoEscena
    {
        public float x;            // metros hacia el este (desde el centro del campus 3D)
        public float z;            // metros hacia el SUR (en Unity: -z)
        public string instruccion;
    }

    [Serializable]
    public class ZonaEscena
    {
        public string nombre;
        public float x;
        public float z;
        public bool es_origen;
        public bool es_destino;
    }

    [Serializable]
    public class Escena
    {
        public string destino;     // nombre del destino (ej: "Aula K-301")
        public ZonaEscena[] zonas;
        public PuntoEscena[] camino;
    }

    [Serializable]
    public class DestinoResumen
    {
        public int id;
        public string nombre;
    }

    [Serializable]
    public class RouteResponse
    {
        public int id;
        public float distancia;
        public int tiempo_minutos;
        public DestinoResumen destino;
        public Escena escena;
    }

    [Serializable]
    public class RouteRequest
    {
        public int origen_id;
        public int destino_id;
    }

    [Serializable]
    public class ErrorApi
    {
        public string detalle;
    }

    // -----------------------------------------------------------------------
    // Cliente HTTP
    // -----------------------------------------------------------------------
    public class ApiClient : MonoBehaviour
    {
        [Header("Servidor de Django")]
        [SerializeField] private string baseUrl = "http://127.0.0.1:8000";
        [SerializeField] private int timeoutSegundos = 10;

        [Header("Sesión (solo editor / escritorio)")]
        [SerializeField] private string sessionId = "";
        [SerializeField] private string csrfToken = "";

        /// <summary>Lo llama la página web (WebGL) con el valor de la cookie csrftoken.</summary>
        public void SetCsrfToken(string token)
        {
            csrfToken = token;
        }

        /// <summary>Calcula la ruta entre una zona y un destino.</summary>
        public void CalculateRoute(int originZoneId, int destinationPlaceId,
                                   Action<RouteResponse> onSuccess, Action<string> onError)
        {
            StartCoroutine(CalcularRuta(originZoneId, destinationPlaceId, onSuccess, onError));
        }

        private IEnumerator CalcularRuta(int origenId, int destinoId,
                                         Action<RouteResponse> alTerminar, Action<string> alFallar)
        {
            string url = baseUrl.TrimEnd('/') + "/api/rutas/calcular/";
            string cuerpo = JsonUtility.ToJson(new RouteRequest { origen_id = origenId, destino_id = destinoId });

            using (UnityWebRequest peticion = new UnityWebRequest(url, UnityWebRequest.kHttpVerbPOST))
            {
                peticion.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(cuerpo));
                peticion.downloadHandler = new DownloadHandlerBuffer();
                peticion.timeout = timeoutSegundos;
                peticion.SetRequestHeader("Content-Type", "application/json");
                peticion.SetRequestHeader("Accept", "application/json");

                if (!string.IsNullOrEmpty(csrfToken))
                    peticion.SetRequestHeader("X-CSRFToken", csrfToken);
#if !UNITY_WEBGL || UNITY_EDITOR
                // Fuera del navegador hay que enviar la cookie de sesión a mano.
                if (!string.IsNullOrEmpty(sessionId))
                    peticion.SetRequestHeader("Cookie", $"sessionid={sessionId}; csrftoken={csrfToken}");
#endif

                yield return peticion.SendWebRequest();

                if (peticion.result == UnityWebRequest.Result.Success)
                    alTerminar?.Invoke(JsonUtility.FromJson<RouteResponse>(peticion.downloadHandler.text));
                else
                    alFallar?.Invoke(LeerMensajeDeError(peticion));
            }
        }

        /// <summary>Extrae el campo "detalle" que devuelve la API en los errores.</summary>
        private static string LeerMensajeDeError(UnityWebRequest peticion)
        {
            if (peticion.responseCode == 403)
                return "Sesión no válida: inicia sesión en la web y actualiza sessionid y csrftoken.";

            string texto = peticion.downloadHandler != null ? peticion.downloadHandler.text : "";
            if (!string.IsNullOrEmpty(texto))
            {
                try
                {
                    ErrorApi error = JsonUtility.FromJson<ErrorApi>(texto);
                    if (error != null && !string.IsNullOrEmpty(error.detalle)) return error.detalle;
                }
                catch (ArgumentException)
                {
                    // La respuesta no era JSON: se usa el mensaje genérico.
                }
            }
            return $"Error {peticion.responseCode}: {peticion.error}";
        }
    }
}
