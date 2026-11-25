// ARCHIVO GENERADO a partir del plano del campus UNEMI (Milagro).
// Unidades: metros. X = Este, Z = Norte. Rotación en grados (horario visto desde arriba).
// Escala usada: 0.45 m por píxel del plano. Origen (0,0,0) = centro aproximado del campus.
// Colores: cada edificio trae su color en formato #RRGGBB (último parámetro).
// Puedes corregir cualquier valor aquí y volver a ejecutar  UNEMI > Generar Campus 3D.
using UnityEngine;

namespace UNEMI.Campus
{
    public static class CampusData
    {
        public const float MetrosPorPixelPlano = 0.45f;

        public static readonly EdificioDef[] Edificios =
        {
            new EdificioDef("POSGRADO", "Posgrado", TipoLugar.Bloque, -53.1f, 119.25f, 36.0f, 20.25f, 10f, 9f, "#2E7D32"),
            new EdificioDef("SIM", "SIM", TipoLugar.Bloque, -19.35f, 86.4f, 22.5f, 15.75f, 15f, 7f, "#1565C0"),
            new EdificioDef("CDIP", "CDIP", TipoLugar.Bloque, -76.5f, 41.4f, 56.25f, 76.5f, 6f, 12f, "#6A1B9A"),
            new EdificioDef("CRAI", "CRAI", TipoLugar.Bloque, -8.1f, 27.0f, 42.75f, 24.75f, 0f, 10f, "#C62828"),
            new EdificioDef("CRAI_N", "", TipoLugar.Edificio, -8.1f, 42.75f, 20.25f, 18.0f, 0f, 10f, "#C62828"),
            new EdificioDef("R", "Bloque R", TipoLugar.Bloque, -95.85f, -33.75f, 24.75f, 24.75f, 5f, 9f, "#00838F"),
            new EdificioDef("ED_M_N", "Bloque L", TipoLugar.Bloque, -27.0f, -24.75f, 33.75f, 15.75f, 5f, 8f, "#AD1457"),
            new EdificioDef("M", "Bloque M", TipoLugar.Bloque, -38.25f, -54.0f, 38.25f, 18.0f, 5f, 9f, "#4E342E"),
            new EdificioDef("N", "Bloque N", TipoLugar.Bloque, -40.5f, -87.75f, 36.0f, 15.75f, 5f, 9f, "#00BFA5"),
            new EdificioDef("S", "Bloque S", TipoLugar.Bloque, -94.5f, -76.5f, 29.25f, 20.25f, 5f, 9f, "#283593"),
            new EdificioDef("T", "Bloque T (FACI)", TipoLugar.Bloque, -108.9f, -108.0f, 31.5f, 18.0f, 8f, 9f, "#558B2F"),
            new EdificioDef("U", "Bloque U", TipoLugar.Bloque, -117.9f, -153.0f, 31.5f, 24.75f, 8f, 9f, "#0277BD"),
            new EdificioDef("O", "Bloque O", TipoLugar.Bloque, -54.0f, -139.5f, 27.0f, 18.0f, 5f, 9f, "#00695C"),
            new EdificioDef("P", "Bloque P", TipoLugar.Bloque, -51.75f, -177.75f, 24.75f, 18.0f, 5f, 9f, "#8E24AA"),
            new EdificioDef("J", "Bloque J", TipoLugar.Bloque, -11.25f, -173.25f, 36.0f, 18.0f, 5f, 9f, "#5D4037"),
            new EdificioDef("K", "Bloque K", TipoLugar.Bloque, 5.85f, -194.4f, 40.5f, 15.75f, 5f, 12f, "#F57C00"),
            new EdificioDef("BANOS_1", "Baños", TipoLugar.Servicio, -32.85f, -201.15f, 27.0f, 11.25f, 5f, 4f, "#B0BEC5"),
            new EdificioDef("I", "Bloque I", TipoLugar.Bloque, 0.0f, -143.1f, 29.25f, 18.0f, 5f, 9f, "#1B5E20"),
            new EdificioDef("H", "Bloque H", TipoLugar.Bloque, 21.15f, -81.0f, 24.75f, 56.25f, 5f, 12f, "#3949AB"),
            new EdificioDef("ED_H_N", "Bloque F", TipoLugar.Bloque, 20.25f, -47.25f, 18.0f, 9.0f, 5f, 6f, "#E53935"),
            new EdificioDef("B", "Bloque B", TipoLugar.Bloque, 64.35f, -56.25f, 40.5f, 24.75f, 5f, 9f, "#43A047"),
            new EdificioDef("ED_B_N", "", TipoLugar.Edificio, 68.4f, -36.9f, 29.25f, 12.6f, 5f, 6f, "#039BE5"),
            new EdificioDef("C", "Bloque C", TipoLugar.Bloque, 67.5f, -108.0f, 29.25f, 18.0f, 5f, 9f, "#7CB342"),
            new EdificioDef("ED_C_O", "", TipoLugar.Edificio, 42.75f, -110.25f, 11.25f, 11.25f, 5f, 5f, "#FDD835"),
            new EdificioDef("E", "Bloque E", TipoLugar.Bloque, 69.75f, -139.5f, 29.25f, 22.5f, 5f, 9f, "#00ACC1"),
            new EdificioDef("BANOS_2", "Baños", TipoLugar.Servicio, 41.4f, -150.3f, 11.25f, 13.5f, 5f, 4f, "#B0BEC5"),
            new EdificioDef("ED_POSG", "", TipoLugar.Edificio, 0.0f, 117.0f, 13.5f, 13.5f, 17f, 5f, "#8D6E63"),
            new EdificioDef("BANOS_3", "Baños", TipoLugar.Servicio, 62.1f, 57.6f, 11.25f, 18.0f, 17f, 4f, "#B0BEC5"),
            new EdificioDef("BIOTEC", "Bloque de Investigación de Biotecnología", TipoLugar.Bloque, 45.0f, 315.0f, 49.5f, 36.0f, 0f, 10f, "#5E35B1"),
        };

        public static readonly ArcoDef[] Arcos =
        {
            new ArcoDef("V", "Bloque V", -22.5f, 139.5f, 36.0f, 67.5f, 115f, 165f, 12f, "#D81B60"),
            new ArcoDef("W", "Bloque W", -22.5f, 139.5f, 42.75f, 74.25f, 55f, 110f, 12f, "#26A69A"),
            new ArcoDef("X", "Bloque X", -22.5f, 139.5f, 22.5f, 54.0f, -20f, 48f, 12f, "#9E9D24"),
        };

        public static readonly AreaDef[] Areas =
        {
            new AreaDef("PISCINA", "Piscina UNEMI", TipoLugar.Deportivo, 79.65f, 171.0f, 53.1f, 89.1f, 17f, "agua"),
            new AreaDef("CANCHA1", "", TipoLugar.Deportivo, 21.6f, 108.9f, 24.75f, 27.0f, 17f, "cancha"),
            new AreaDef("CANCHA2", "", TipoLugar.Deportivo, 42.75f, 102.6f, 20.25f, 27.0f, 17f, "cancha"),
            new AreaDef("CANCHA3", "Canchas", TipoLugar.Deportivo, 62.1f, 94.5f, 20.25f, 24.75f, 17f, "cancha"),
            new AreaDef("CANCHA4", "", TipoLugar.Deportivo, 27.0f, 72.0f, 15.75f, 18.0f, 17f, "cancha"),
            new AreaDef("CANCHA5", "", TipoLugar.Deportivo, 45.0f, 65.25f, 15.75f, 18.0f, 17f, "cancha"),
            new AreaDef("PARQ1", "Estacionamiento 1", TipoLugar.Estacionamiento, 112.5f, 308.25f, 54.0f, 49.5f, 0f, "parqueo"),
            new AreaDef("PARQ2", "Estacionamiento 2", TipoLugar.Estacionamiento, -191.25f, -211.5f, 103.5f, 90.0f, 26f, "parqueo"),
            new AreaDef("VERDE1", "Área Verde", TipoLugar.AreaVerde, -149.85f, -76.5f, 36.0f, 130.5f, 12f, "verde"),
            new AreaDef("VERDE2", "Área Verde", TipoLugar.AreaVerde, -45.0f, -266.4f, 211.5f, 67.5f, 26f, "verde"),
        };

        public static readonly AreaDef Estadio = new AreaDef("ESTADIO", "Estadio Universitario UNEMI", TipoLugar.Deportivo, 139.5f, 87.75f, 114.75f, 180.0f, 19f, "pista");

        public static readonly PuntoDef[] Entradas =
        {
            new PuntoDef("ENTRADA_PEATONAL", "Entrada peatonal", TipoLugar.Entrada, 105.75f, -108.0f),
            new PuntoDef("SALIDA_VEHICULOS", "Salida de vehículos", TipoLugar.SalidaVehicular, 57.6f, -209.25f),
            new PuntoDef("ENTRADA_VEHICULOS", "Entrada de vehículos", TipoLugar.EntradaVehicular, 147.6f, 338.4f),
        };

        public static readonly PuntoDef Monumento = new PuntoDef("MONUMENTO", "Monumento de las Banderas", TipoLugar.Monumento, 104.4f, 263.25f);

        public static readonly LineaDef[] Calles =
        {
            new LineaDef("Avenida 17 de Septiembre", 16f, "avenida", new[] { new Vector2(368.1f, 396.0f), new Vector2(31.95f, -328.5f) }),
            new LineaDef("", 7f, "calle", new[] { new Vector2(-162.0f, 204.75f), new Vector2(-90.0f, 294.75f) }),
            new LineaDef("", 7f, "calle", new[] { new Vector2(-162.0f, 204.75f), new Vector2(-130.5f, 180.0f), new Vector2(-94.5f, 153.0f), new Vector2(-85.5f, 126.0f), new Vector2(-90.0f, 92.25f), new Vector2(-108.0f, 0.0f), new Vector2(-128.25f, -90.0f), new Vector2(-146.25f, -162.0f) }),
            new LineaDef("", 6f, "calle", new[] { new Vector2(-90.0f, 92.25f), new Vector2(-31.5f, 90.0f), new Vector2(45.0f, 54.0f) }),
            new LineaDef("", 6f, "calle", new[] { new Vector2(-33.75f, 114.75f), new Vector2(-45.0f, 0.0f), new Vector2(-63.0f, -90.0f), new Vector2(-83.25f, -189.0f) }),
            new LineaDef("", 7f, "calle", new[] { new Vector2(-112.5f, 2.25f), new Vector2(-9.0f, -6.75f), new Vector2(103.5f, -20.25f), new Vector2(139.5f, -20.25f), new Vector2(209.25f, 63.0f) }),
            new LineaDef("", 6f, "calle", new[] { new Vector2(45.0f, 54.0f), new Vector2(48.6f, -15.75f) }),
            new LineaDef("", 6f, "calle", new[] { new Vector2(101.25f, -20.25f), new Vector2(99.0f, -74.25f), new Vector2(150.75f, -74.25f) }),
            new LineaDef("", 7f, "calle", new[] { new Vector2(-225.0f, -128.25f), new Vector2(49.5f, -265.5f), new Vector2(81.0f, -281.25f) }),
            new LineaDef("", 6f, "calle", new[] { new Vector2(99.0f, -74.25f), new Vector2(93.6f, -171.0f), new Vector2(49.5f, -189.0f), new Vector2(27.0f, -234.0f) }),
            new LineaDef("Vía de acceso vehicular", 7f, "calle", new[] { new Vector2(147.6f, 338.4f), new Vector2(108.0f, 343.8f), new Vector2(45.0f, 345.6f), new Vector2(-18.0f, 336.6f), new Vector2(-90.0f, 294.75f) }),
            new LineaDef("", 3f, "sendero", new[] { new Vector2(92.7f, 212.85f), new Vector2(104.4f, 263.25f), new Vector2(111.6f, 282.6f), new Vector2(109.35f, 342.0f) }),
            new LineaDef("", 3f, "sendero", new[] { new Vector2(-83.25f, -189.0f), new Vector2(-31.5f, -215.1f), new Vector2(27.0f, -231.75f) }),
            new LineaDef("Paseo central", 4f, "peatonal", new[] { new Vector2(-5.85f, -7.65f), new Vector2(-5.85f, -123.75f) }),
            new LineaDef("Paseo de los bloques", 4f, "peatonal", new[] { new Vector2(-69.75f, -123.75f), new Vector2(96.3f, -123.75f) }),
            new LineaDef("", 4f, "peatonal", new[] { new Vector2(-77.4f, -159.75f), new Vector2(94.05f, -159.75f) }),
            new LineaDef("", 4f, "peatonal", new[] { new Vector2(32.4f, -159.75f), new Vector2(32.4f, -223.2f) }),
            new LineaDef("", 4f, "peatonal", new[] { new Vector2(25.2f, -123.75f), new Vector2(25.2f, -159.75f) }),
            new LineaDef("", 4f, "peatonal", new[] { new Vector2(39.15f, -13.05f), new Vector2(39.15f, -95.85f) }),
            new LineaDef("", 2.5f, "peatonal", new[] { new Vector2(39.15f, -95.85f), new Vector2(34.2f, -99.9f), new Vector2(34.2f, -123.75f) }),
            new LineaDef("", 4f, "peatonal", new[] { new Vector2(47.25f, 18.0f), new Vector2(74.7f, 18.0f), new Vector2(74.7f, 90.0f), new Vector2(90.9f, 129.6f) }),
        };

        public static readonly LineaDef Estero = new LineaDef("Estero de Belín", 6f, "estero", new[] { new Vector2(-234.0f, -67.5f), new Vector2(-212.4f, -47.25f), new Vector2(-162.0f, 0.0f), new Vector2(-128.25f, 45.0f), new Vector2(-122.4f, 135.0f), new Vector2(-112.5f, 180.0f), new Vector2(-94.5f, 204.75f), new Vector2(-54.0f, 222.75f), new Vector2(87.75f, 258.75f), new Vector2(162.0f, 238.5f), new Vector2(209.25f, 216.0f), new Vector2(234.0f, 198.0f) });
    }
}
