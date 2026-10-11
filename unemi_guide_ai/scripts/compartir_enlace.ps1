<#
==========================================================================
 UNEMI Guide AI · Compartir la app con un enlace público (HTTPS)
--------------------------------------------------------------------------
 Crea un enlace https://....trycloudflare.com que apunta a esta PC, para
 que cualquier persona entre desde su celular o computadora, aunque esté
 en otra red.

 Qué hace, en orden:
   1. Verifica que exista el entorno virtual (venv).
   2. Instala cloudflared con winget si no está instalado.
   3. Arranca el servidor de Django (o usa el que ya esté encendido).
   4. Abre el túnel de Cloudflare y muestra el enlace (y lo copia).
   5. Al presionar Enter, cierra el túnel (y el servidor, si lo abrió él).

 Uso: doble clic en compartir_enlace.bat (carpeta raíz del proyecto).
==========================================================================
#>

$ErrorActionPreference = "Stop"
$PUERTO = 8000
$SEGUNDOS_ESPERA_ENLACE = 60

# --- Rutas del proyecto (este script vive en unemi_guide_ai\scripts\) ----
$raiz = Split-Path $PSScriptRoot -Parent
$backend = Join-Path $raiz "backend"
$python = Join-Path $raiz "venv\Scripts\python.exe"
$registroTunel = Join-Path $env:TEMP "unemi_guide_tunel.log"

function Escribir-Titulo($texto) {
    Write-Host ""
    Write-Host "  $texto" -ForegroundColor Cyan
}

function Terminar-ConError($mensaje) {
    Write-Host ""
    Write-Host "  ERROR: $mensaje" -ForegroundColor Red
    Read-Host "  Presiona Enter para salir"
    exit 1
}

Write-Host ""
Write-Host "  ==============================================" -ForegroundColor Blue
Write-Host "     UNEMI Guide AI  ·  Compartir enlace público" -ForegroundColor Blue
Write-Host "  ==============================================" -ForegroundColor Blue

# ------------------------------------------------------------------
# 1. Entorno virtual
# ------------------------------------------------------------------
if (-not (Test-Path $python)) {
    Terminar-ConError "No existe el entorno virtual en $raiz\venv. Créalo con: python -m venv venv"
}

# ------------------------------------------------------------------
# 2. cloudflared (se instala solo la primera vez)
# ------------------------------------------------------------------
function Buscar-Cloudflared {
    $comando = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($comando) { return $comando.Source }
    # Recién instalado, puede no estar aún en el PATH de esta ventana.
    foreach ($ruta in @(
            "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe",
            "$env:ProgramFiles\cloudflared\cloudflared.exe",
            "$env:LOCALAPPDATA\Microsoft\WinGet\Links\cloudflared.exe")) {
        if (Test-Path $ruta) { return $ruta }
    }
    return $null
}

$cloudflared = Buscar-Cloudflared
if (-not $cloudflared) {
    Escribir-Titulo "Instalando cloudflared (solo la primera vez)..."
    winget install --id Cloudflare.cloudflared -e --accept-source-agreements --accept-package-agreements
    $cloudflared = Buscar-Cloudflared
    if (-not $cloudflared) {
        Terminar-ConError "No se pudo instalar cloudflared. Instálalo a mano: winget install --id Cloudflare.cloudflared"
    }
}

# ------------------------------------------------------------------
# 3. Servidor de Django
# ------------------------------------------------------------------
$servidorPropio = $null
$escuchando = Get-NetTCPConnection -LocalPort $PUERTO -State Listen -ErrorAction SilentlyContinue
if ($escuchando) {
    Escribir-Titulo "Usando el servidor que ya está encendido en el puerto $PUERTO."
} else {
    Escribir-Titulo "Encendiendo el servidor de Django (se abre en otra ventana)..."
    $servidorPropio = Start-Process -FilePath $python `
        -ArgumentList "manage.py", "runserver", "$PUERTO" `
        -WorkingDirectory $backend -PassThru
    # Espera a que el servidor responda (máximo 30 s).
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        if (Get-NetTCPConnection -LocalPort $PUERTO -State Listen -ErrorAction SilentlyContinue) { break }
    }
    if (-not (Get-NetTCPConnection -LocalPort $PUERTO -State Listen -ErrorAction SilentlyContinue)) {
        Terminar-ConError "El servidor no arrancó. Revisa la otra ventana para ver el error."
    }
}

# ------------------------------------------------------------------
# 4. Túnel de Cloudflare
# ------------------------------------------------------------------
Escribir-Titulo "Creando el enlace público (tarda unos segundos)..."
if (Test-Path $registroTunel) { Remove-Item $registroTunel -Force }

$tunel = Start-Process -FilePath $cloudflared `
    -ArgumentList "tunnel", "--url", "http://localhost:$PUERTO" `
    -RedirectStandardError $registroTunel -NoNewWindow -PassThru

# cloudflared escribe el enlace en su registro: lo buscamos ahí.
$enlace = $null
for ($i = 0; $i -lt $SEGUNDOS_ESPERA_ENLACE -and -not $enlace; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Path $registroTunel) {
        $coincidencia = Select-String -Path $registroTunel -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" |
            Select-Object -First 1
        if ($coincidencia) { $enlace = $coincidencia.Matches[0].Value }
    }
}

if (-not $enlace) {
    Stop-Process -Id $tunel.Id -Force -ErrorAction SilentlyContinue
    Terminar-ConError "No se obtuvo el enlace. Revisa tu conexión a internet e intenta de nuevo."
}

Set-Clipboard -Value $enlace

Write-Host ""
Write-Host "  ==============================================" -ForegroundColor Green
Write-Host "   ENLACE PARA COMPARTIR (ya está copiado):" -ForegroundColor Green
Write-Host ""
Write-Host "   $enlace" -ForegroundColor Yellow
Write-Host ""
Write-Host "  ==============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Cómo compartirlo:"
Write-Host "   1. Pega el enlace (Ctrl + V) en WhatsApp, correo, etc."
Write-Host "   2. La persona necesita usuario y contraseña: créalos en"
Write-Host "      $enlace/admin/  (Usuarios -> Añadir, SIN 'Staff status')."
Write-Host ""
Write-Host "  Importante:"
Write-Host "   - El enlace funciona MIENTRAS esta ventana esté abierta."
Write-Host "   - Cada vez que ejecutes este script, el enlace será otro."
Write-Host ""

# ------------------------------------------------------------------
# 5. Cerrar todo al terminar
# ------------------------------------------------------------------
Read-Host "  Presiona Enter para CERRAR el enlace"

Stop-Process -Id $tunel.Id -Force -ErrorAction SilentlyContinue
if ($servidorPropio) {
    Stop-Process -Id $servidorPropio.Id -Force -ErrorAction SilentlyContinue
}
Write-Host "  Enlace cerrado. Ya nadie puede entrar desde internet." -ForegroundColor Green
Start-Sleep -Seconds 2
