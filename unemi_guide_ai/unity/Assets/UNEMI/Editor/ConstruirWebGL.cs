using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace UNEMI.Campus.EditorTools
{
    /// <summary>
    /// Menú  UNEMI > Construir WebGL para la web
    ///
    /// Genera la escena del campus (con UNEMICampusBuilder), compila el build WebGL
    /// y copia los archivos a backend/web/static/web/unity/Build, donde Django los
    /// encuentra solo. También se puede ejecutar sin abrir Unity:
    ///
    ///   Unity.exe -batchmode -quit -projectPath unity -executeMethod UNEMI.Campus.EditorTools.ConstruirWebGL.Construir
    ///
    /// (eso hace herramientas/construir_webgl.ps1).
    /// </summary>
    public static class ConstruirWebGL
    {
        const string Escena = "Assets/UNEMI/Escenas/CampusUNEMI.unity";
        const string CarpetaTemporal = "Builds/WebGL";
        const string NombreBuild = "unemi";

        /// <summary>backend/web/static/web/unity/Build (relativo a la carpeta del proyecto Unity).</summary>
        static string CarpetaDestino =>
            Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "backend", "web", "static", "web", "unity", "Build"));

        [MenuItem("UNEMI/Construir WebGL para la web", priority = 40)]
        public static void ConstruirDesdeMenu()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            bool ok = Ejecutar();
            EditorUtility.DisplayDialog("Campus UNEMI",
                ok ? "Build WebGL copiado a:\n" + CarpetaDestino + "\n\nRecarga la página web."
                   : "El build falló. Revisa la consola.", "OK");
        }

        /// <summary>Punto de entrada para -executeMethod (modo batch).</summary>
        public static void Construir()
        {
            bool ok = false;
            try { ok = Ejecutar(); }
            catch (Exception e) { Debug.LogException(e); }
            if (Application.isBatchMode) EditorApplication.Exit(ok ? 0 : 1);
        }

        static bool Ejecutar()
        {
            // 1) Escena nueva y campus generado desde CampusData.cs (siempre al día)
            EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
            UNEMICampusBuilder.Generar();
            if (!File.Exists(Escena))
            {
                Debug.LogError("[UNEMI] No se guardó la escena " + Escena);
                return false;
            }
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(Escena, true) };

            // 2) Ajustes WebGL: sin compresión (Django los sirve tal cual) y nombre fijo
            if (EditorUserBuildSettings.activeBuildTarget != BuildTarget.WebGL)
                EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.WebGL, BuildTarget.WebGL);
            PlayerSettings.companyName = "UNEMI";
            PlayerSettings.productName = "UNEMI Guide AI";
            PlayerSettings.WebGL.compressionFormat = WebGLCompressionFormat.Disabled;
            PlayerSettings.WebGL.decompressionFallback = false;
            PlayerSettings.WebGL.dataCaching = false;
            PlayerSettings.runInBackground = true;

            // 3) Build
            string salida = Path.GetFullPath(Path.Combine(Application.dataPath, "..", CarpetaTemporal, NombreBuild));
            if (Directory.Exists(salida)) Directory.Delete(salida, true);
            var opciones = new BuildPlayerOptions
            {
                scenes = new[] { Escena },
                locationPathName = salida,
                target = BuildTarget.WebGL,
                options = BuildOptions.None,
            };
            var reporte = BuildPipeline.BuildPlayer(opciones);
            if (reporte.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded)
            {
                Debug.LogError("[UNEMI] Build WebGL falló: " + reporte.summary.result +
                               " (" + reporte.summary.totalErrors + " errores)");
                return false;
            }

            // 4) Copiar Build/* a la web (se borra el build anterior)
            string origen = Path.Combine(salida, "Build");
            string destino = CarpetaDestino;
            Directory.CreateDirectory(destino);
            foreach (var viejo in Directory.GetFiles(destino)) File.Delete(viejo);
            foreach (var archivo in Directory.GetFiles(origen))
                File.Copy(archivo, Path.Combine(destino, Path.GetFileName(archivo)), true);

            Debug.Log("[UNEMI] Build WebGL listo en " + destino);
            return true;
        }
    }
}
