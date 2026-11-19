# Construye el campus 3D de Unity para la web, sin abrir el editor.
#
#   powershell -ExecutionPolicy Bypass -File unity\herramientas\construir_webgl.ps1
#
# Requisitos: Unity (con el módulo "WebGL Build Support") instalado desde Unity Hub
# y haber iniciado sesión una vez en Unity Hub (licencia Personal gratuita).
# Resultado: backend\web\static\web\unity\Build\unemi.* (Django lo detecta solo).
param(
    [string]$Unity = ""   # Ruta a Unity.exe (opcional; si no, se busca sola)
)
$ErrorActionPreference = "Stop"
$proyecto = Resolve-Path (Join-Path $PSScriptRoot "..")
$log = Join-Path $proyecto "Logs\construir_webgl.log"

if (-not $Unity) {
    $candidatos = @()
    $bases = @("$env:ProgramFiles\Unity\Hub\Editor", "$env:USERPROFILE\Unity\Hub\Editor", "$env:ProgramFiles\Unity*\Editor", "C:\Unity\*\Editor")
    # Carpeta elegida en Unity Hub (Preferences > Installs), si existe
    $archivoHub = Join-Path $env:APPDATA "UnityHub\secondaryInstallPath.json"
    if (Test-Path $archivoHub) { $bases += (Get-Content $archivoHub -Raw | ConvertFrom-Json) }
    foreach ($base in $bases) {
        $candidatos += Get-ChildItem -Path $base -Filter Unity.exe -Recurse -Depth 3 -ErrorAction SilentlyContinue
    }
    # Solo editores con WebGL instalado; el más nuevo primero
    $conWebGL = $candidatos | Where-Object { Test-Path (Join-Path $_.DirectoryName "Data\PlaybackEngines\WebGLSupport") } |
        Sort-Object { $_.Directory.Parent.Name } -Descending
    if (-not $conWebGL) {
        Write-Host "No se encontró Unity con el módulo WebGL." -ForegroundColor Red
        Write-Host "Instala Unity Hub, luego un editor (6000.x LTS) con 'WebGL Build Support'."
        exit 1
    }
    $Unity = $conWebGL[0].FullName
}

New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
Write-Host "Unity:    $Unity"
Write-Host "Proyecto: $proyecto"
Write-Host "Log:      $log"
Write-Host "Construyendo (la primera vez tarda 5-15 minutos)..."

$proceso = Start-Process -FilePath $Unity -Wait -PassThru -NoNewWindow -ArgumentList @(
    "-batchmode", "-quit",
    "-projectPath", "`"$proyecto`"",
    "-buildTarget", "WebGL",
    "-executeMethod", "UNEMI.Campus.EditorTools.ConstruirWebGL.Construir",
    "-logFile", "`"$log`""
)

if ($proceso.ExitCode -ne 0) {
    Write-Host "El build falló (código $($proceso.ExitCode)). Últimas líneas del log:" -ForegroundColor Red
    Get-Content $log -Tail 40
    if (Select-String -Path $log -Pattern "license|licen" -Quiet) {
        Write-Host "`nParece un problema de licencia: abre Unity Hub e inicia sesión (licencia Personal)." -ForegroundColor Yellow
    }
    exit $proceso.ExitCode
}
Write-Host "Listo. Recarga la página web: el recorrido 3D ya usa Unity." -ForegroundColor Green
