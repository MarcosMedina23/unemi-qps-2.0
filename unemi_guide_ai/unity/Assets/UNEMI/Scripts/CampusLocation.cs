using System;
using System.Collections.Generic;
using UnityEngine;

namespace UNEMI.Campus
{
    /// <summary>
    /// Marca un lugar del campus (bloque, estacionamiento, entrada, aula...).
    /// El proyecto del GPS puede buscar destinos con CampusLocation.Buscar("K") o Buscar("K-301").
    /// </summary>
    [DisallowMultipleComponent]
    public class CampusLocation : MonoBehaviour
    {
        [Tooltip("Identificador corto y único. Ej: K, CDIP, PARQ1, ENTRADA1, K-301")]
        public string id;

        [Tooltip("Nombre que se muestra al usuario")]
        public string nombre;

        public TipoLugar tipo;

        [Tooltip("Punto exacto de llegada (puerta). Si está vacío se usa el centro del lugar.")]
        public Transform puntoAcceso;

        static readonly List<CampusLocation> registrados = new List<CampusLocation>();

        void OnEnable()
        {
            if (!registrados.Contains(this)) registrados.Add(this);
        }

        void OnDisable()
        {
            registrados.Remove(this);
        }

        /// <summary>Posición a la que debe llegar la navegación (a nivel del suelo).</summary>
        public Vector3 PosicionDestino
        {
            get
            {
                Vector3 p = puntoAcceso != null ? puntoAcceso.position : transform.position;
                return new Vector3(p.x, 0f, p.z);
            }
        }

        /// <summary>Todos los lugares de la escena.</summary>
        public static IReadOnlyList<CampusLocation> Todos
        {
            get
            {
                if (registrados.Count == 0)
                {
#if UNITY_2023_1_OR_NEWER
                    registrados.AddRange(UnityEngine.Object.FindObjectsByType<CampusLocation>(FindObjectsSortMode.None));
#else
                    registrados.AddRange(UnityEngine.Object.FindObjectsOfType<CampusLocation>());
#endif
                }
                return registrados;
            }
        }

        /// <summary>Busca por id exacto, luego por nombre exacto y por último por nombre parcial (sin importar mayúsculas).</summary>
        public static CampusLocation Buscar(string texto)
        {
            if (string.IsNullOrWhiteSpace(texto)) return null;
            texto = texto.Trim();
            var lista = Todos;

            foreach (var l in lista)
                if (l != null && string.Equals(l.id, texto, StringComparison.OrdinalIgnoreCase)) return l;
            foreach (var l in lista)
                if (l != null && string.Equals(l.nombre, texto, StringComparison.OrdinalIgnoreCase)) return l;
            foreach (var l in lista)
                if (l != null && !string.IsNullOrEmpty(l.nombre) &&
                    l.nombre.IndexOf(texto, StringComparison.OrdinalIgnoreCase) >= 0) return l;
            return null;
        }

        /// <summary>Lugares de un tipo concreto (ej: todas las entradas).</summary>
        public static List<CampusLocation> PorTipo(TipoLugar t)
        {
            var r = new List<CampusLocation>();
            foreach (var l in Todos) if (l != null && l.tipo == t) r.Add(l);
            return r;
        }

        void OnDrawGizmosSelected()
        {
            Gizmos.color = Color.yellow;
            Gizmos.DrawWireSphere(PosicionDestino, 2f);
        }
    }
}
