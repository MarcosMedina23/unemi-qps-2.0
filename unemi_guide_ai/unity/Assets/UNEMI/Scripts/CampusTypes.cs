using UnityEngine;

namespace UNEMI.Campus
{
    /// <summary>Tipo de lugar dentro del campus (útil para filtrar en el GPS).</summary>
    public enum TipoLugar
    {
        Bloque,
        Edificio,
        Servicio,
        Deportivo,
        Estacionamiento,
        AreaVerde,
        Entrada,
        EntradaVehicular,
        SalidaVehicular,
        Monumento,
        Aula,
        Calle,
        Agua
    }

    /// <summary>Edificio rectangular. Medidas en metros, rotación en grados (eje Y de Unity).
    /// Estilo = color "#RRGGBB" del edificio.</summary>
    public struct EdificioDef
    {
        public readonly string Id, Nombre, Estilo;
        public readonly TipoLugar Tipo;
        public readonly float X, Z, Ancho, Largo, Rot, Alto;

        public EdificioDef(string id, string nombre, TipoLugar tipo, float x, float z,
                           float ancho, float largo, float rot, float alto, string estilo)
        {
            Id = id; Nombre = nombre; Tipo = tipo; X = x; Z = z;
            Ancho = ancho; Largo = largo; Rot = rot; Alto = alto; Estilo = estilo;
        }
    }

    /// <summary>Edificio curvo (sector de anillo). Ángulos en grados, antihorario desde el Este.</summary>
    public struct ArcoDef
    {
        public readonly string Id, Nombre, Estilo;
        public readonly float CX, CZ, RadioInterior, RadioExterior, AnguloInicio, AnguloFin, Alto;

        public ArcoDef(string id, string nombre, float cx, float cz, float rIn, float rOut,
                       float a0, float a1, float alto, string estilo)
        {
            Id = id; Nombre = nombre; CX = cx; CZ = cz; RadioInterior = rIn; RadioExterior = rOut;
            AnguloInicio = a0; AnguloFin = a1; Alto = alto; Estilo = estilo;
        }

        public float AnguloMedio => (AnguloInicio + AnguloFin) * 0.5f;
        public float RadioMedio => (RadioInterior + RadioExterior) * 0.5f;

        /// <summary>Centro del bloque (punto medio del arco) en coordenadas del campus.</summary>
        public Vector2 CentroBloque
        {
            get
            {
                float a = AnguloMedio * Mathf.Deg2Rad;
                return new Vector2(CX + RadioMedio * Mathf.Cos(a), CZ + RadioMedio * Mathf.Sin(a));
            }
        }
    }

    /// <summary>Zona plana: estacionamientos, áreas verdes, canchas, piscina, estadio.</summary>
    public struct AreaDef
    {
        public readonly string Id, Nombre, Estilo;
        public readonly TipoLugar Tipo;
        public readonly float X, Z, Ancho, Largo, Rot;

        public AreaDef(string id, string nombre, TipoLugar tipo, float x, float z,
                       float ancho, float largo, float rot, string estilo)
        {
            Id = id; Nombre = nombre; Tipo = tipo; X = x; Z = z;
            Ancho = ancho; Largo = largo; Rot = rot; Estilo = estilo;
        }
    }

    /// <summary>Punto suelto (entradas).</summary>
    public struct PuntoDef
    {
        public readonly string Id, Nombre;
        public readonly TipoLugar Tipo;
        public readonly float X, Z;

        public PuntoDef(string id, string nombre, TipoLugar tipo, float x, float z)
        {
            Id = id; Nombre = nombre; Tipo = tipo; X = x; Z = z;
        }
    }

    /// <summary>Polilínea: calles y estero.</summary>
    public struct LineaDef
    {
        public readonly string Nombre, Estilo;
        public readonly float Ancho;
        public readonly Vector2[] Puntos;

        public LineaDef(string nombre, float ancho, string estilo, Vector2[] puntos)
        {
            Nombre = nombre; Ancho = ancho; Estilo = estilo; Puntos = puntos;
        }
    }
}
