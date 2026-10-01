<#
Crea el acceso directo en la carpeta de Inicio de Windows del usuario
ACTUAL para que actualizar_remoto_loop.ps1 arranque solo la proxima vez
que se inicie sesion en esta maquina. No pide permisos de administrador:
usa la carpeta de Inicio personal (shell:startup), no la de todos los
usuarios (esa si pide admin).

Correrlo UNA sola vez, desde una consola de PowerShell parada en esta
misma carpeta del repo:
  powershell -ExecutionPolicy Bypass -File instalar_inicio_automatico.ps1

Para sacarlo mas adelante: borrar el acceso directo que deja creado
("Actualizar snapshot bebidas.lnk") de la carpeta de Inicio (Win+R,
escribir shell:startup, Enter).
#>

$ErrorActionPreference = "Stop"

$scriptLoop = Join-Path $PSScriptRoot "actualizar_remoto_loop.ps1"
if (-not (Test-Path $scriptLoop)) {
    throw "No se encontro actualizar_remoto_loop.ps1 en $PSScriptRoot -- correr este script desde la carpeta del repo clonado."
}

$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "Actualizar snapshot bebidas.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptLoop`""
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Description = "Actualiza el snapshot de stock de bebidas y lo sube a git -- ver README.md, seccion Automatizar la actualizacion desde un servidor remoto"
$shortcut.Save()

Write-Host "Acceso directo creado en: $shortcutPath"
Write-Host "A partir de ahora arranca solo cada vez que inicies sesion en Windows en esta maquina."
Write-Host "Para probarlo ya mismo sin reiniciar sesion, hace doble clic en ese acceso directo."
