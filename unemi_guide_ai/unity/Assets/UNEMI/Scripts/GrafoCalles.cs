using System.Collections.Generic;
using UnityEngine;

namespace UNEMI.Campus
{
    /// <summary>
    /// Grafo de las calles y senderos del campus (sale de CampusData.Calles) y
    /// camino más corto con Dijkstra, para que la personita camine por las calles
    /// y no atraviese los edificios.
    ///
    /// Cómo se arma:
    ///  1. Cada calle se parte en puntos cada "PasoMetros" metros (nodos).
    ///  2. Los puntos seguidos de una misma calle se conectan.
    ///  3. Dos puntos de calles distintas que estén a menos de "DistanciaCruce"
    ///     metros también se conectan (así se forman los cruces).
    /// La Avenida 17 de Septiembre no entra: está fuera del campus (igual que en Django).
    /// </summary>
    public static class GrafoCalles
    {
        const float PasoMetros = 8f;
        const float DistanciaCruce = 9f;

        static List<Vector2> nodos;
        static List<List<int>> vecinos;

        static void Construir()
        {
            nodos = new List<Vector2>();
            vecinos = new List<List<int>>();
            var calleDeNodo = new List<int>();

            for (int c = 0; c < CampusData.Calles.Length; c++)
            {
                if (CampusData.Calles[c].Estilo == "avenida") continue;
                Vector2[] p = CampusData.Calles[c].Puntos;
                int anterior = AgregarNodo(p[0], c, calleDeNodo);
                for (int i = 0; i < p.Length - 1; i++)
                {
                    int pasos = Mathf.Max(1, Mathf.CeilToInt(Vector2.Distance(p[i], p[i + 1]) / PasoMetros));
                    for (int k = 1; k <= pasos; k++)
                    {
                        int actual = AgregarNodo(Vector2.Lerp(p[i], p[i + 1], (float)k / pasos), c, calleDeNodo);
                        Conectar(anterior, actual);
                        anterior = actual;
                    }
                }
            }

            // Cruces entre calles distintas
            for (int a = 0; a < nodos.Count; a++)
                for (int b = a + 1; b < nodos.Count; b++)
                    if (calleDeNodo[a] != calleDeNodo[b] && Vector2.Distance(nodos[a], nodos[b]) <= DistanciaCruce)
                        Conectar(a, b);
        }

        static int AgregarNodo(Vector2 punto, int calle, List<int> calleDeNodo)
        {
            nodos.Add(punto);
            vecinos.Add(new List<int>());
            calleDeNodo.Add(calle);
            return nodos.Count - 1;
        }

        static void Conectar(int a, int b)
        {
            vecinos[a].Add(b);
            vecinos[b].Add(a);
        }

        /// <summary>
        /// Puntos de calle para ir de "desde" a "hasta" (sin incluir esos dos puntos).
        /// Si el destino está en una calle sin conexión, llega a la calle alcanzable más cercana.
        /// </summary>
        public static List<Vector3> Camino(Vector3 desde, Vector3 hasta)
        {
            if (nodos == null) Construir();
            var resultado = new List<Vector3>();
            if (nodos.Count == 0) return resultado;

            int inicio = MasCercano(new Vector2(desde.x, desde.z));
            Vector2 meta = new Vector2(hasta.x, hasta.z);

            // ----- Dijkstra (versión simple con arreglos) -----
            int n = nodos.Count;
            var distancia = new float[n];
            var previo = new int[n];
            var visitado = new bool[n];
            for (int i = 0; i < n; i++) { distancia[i] = float.MaxValue; previo[i] = -1; }
            distancia[inicio] = 0f;

            for (int vuelta = 0; vuelta < n; vuelta++)
            {
                // Nodo no visitado con menor distancia
                int u = -1;
                for (int i = 0; i < n; i++)
                    if (!visitado[i] && distancia[i] < float.MaxValue && (u == -1 || distancia[i] < distancia[u])) u = i;
                if (u == -1) break; // ya no hay más nodos alcanzables
                visitado[u] = true;

                foreach (int v in vecinos[u])
                {
                    float nueva = distancia[u] + Vector2.Distance(nodos[u], nodos[v]);
                    if (nueva < distancia[v]) { distancia[v] = nueva; previo[v] = u; }
                }
            }

            // Nodo alcanzable más cercano al destino
            int fin = inicio;
            for (int i = 0; i < n; i++)
                if (visitado[i] && Vector2.Distance(nodos[i], meta) < Vector2.Distance(nodos[fin], meta)) fin = i;

            // Reconstruir el camino de atrás hacia adelante
            for (int i = fin; i != -1; i = previo[i])
                resultado.Insert(0, new Vector3(nodos[i].x, 0f, nodos[i].y));
            return resultado;
        }

        static int MasCercano(Vector2 punto)
        {
            int mejor = 0;
            for (int i = 1; i < nodos.Count; i++)
                if ((nodos[i] - punto).sqrMagnitude < (nodos[mejor] - punto).sqrMagnitude) mejor = i;
            return mejor;
        }
    }
}
