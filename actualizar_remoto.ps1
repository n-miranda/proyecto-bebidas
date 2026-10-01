<#
Corre desatendido (Programador de tareas de Windows) en la maquina con
acceso de red al servidor remoto donde estan los Excel de origen. Genera
el snapshot, lo copia a data\snapshot.json y lo sube a git -- Vercel
redespliega solo al detectar el push. Ver README, seccion "Automatizar la
actualizacion desde un servidor remoto".

Requiere en ESTA maquina:
  - Python 3.11+ con `pip install -r requirements.txt` ya corrido.
  - git configurado con credenciales propias de este repo (un token/deploy
    key con permiso de push, no las credenciales personales de otra
    persona) -- probar a mano "git push" una vez antes de programar la tarea.
  - config\config.local.json con las rutas UNC reales del servidor (copiar
    config\config.local.example.json y completarlo). NUNCA editar
    config\config.json aca: ese lo comparten las demas maquinas.
#>

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$logDir = Join-Path $PSScriptRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir ("actualizar_remoto_{0:yyyyMMdd}.log" -f (Get-Date))

function Escribir-Log($mensaje) {
    $linea = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $mensaje
    Add-Content -Path $logFile -Value $linea
    Write-Host $linea
}

try {
    Escribir-Log "Inicio de actualizacion remota"

    python -m src.actualizar_snapshot
    if ($LASTEXITCODE -ne 0) {
        throw "La generacion del snapshot termino con codigo $LASTEXITCODE (ver logs\actualizar_snapshot_*.log)"
    }

    git add data/snapshot.json

    git diff --cached --quiet
    $hayCambios = ($LASTEXITCODE -ne 0)

    if ($hayCambios) {
        $fecha = Get-Date -Format "yyyy-MM-dd HH:mm"
        git commit -m "Actualizar snapshot publicado ($fecha, automatico)" | Out-String | ForEach-Object { Escribir-Log $_ }
        git push | Out-String | ForEach-Object { Escribir-Log $_ }
        Escribir-Log "Snapshot actualizado y subido a git"
    } else {
        Escribir-Log "Sin cambios en el snapshot -- no se hizo commit"
    }

    Escribir-Log "Fin OK"
} catch {
    Escribir-Log "ERROR: $_"
    exit 1
}
