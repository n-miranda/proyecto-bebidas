<#
Alternativa a "actualizar_remoto.ps1 + Programador de tareas", para cuando
no hay permisos de administrador en la maquina. Algunas opciones del
Programador de tareas (en particular "ejecutar la tarea aunque el usuario
no inicie sesion") piden permisos que no siempre estan disponibles; este
script evita el Programador de tareas por completo.

Corre en bucle, sin fin, mientras la sesion de Windows este abierta: cada
$IntervaloHoras llama a actualizar_remoto.ps1 (genera el snapshot y hace
git push si cambio algo) y vuelve a dormir. No instala nada ni requiere
permisos especiales -- solo necesita que Python, git y el repo ya esten
listos (ver README, seccion "Automatizar la actualizacion desde un
servidor remoto").

Para que arranque solo al iniciar sesion en Windows (sin admin):
  1. Win+R, escribir shell:startup, Enter -- se abre la carpeta de Inicio
     del usuario actual.
  2. Crear ahi un acceso directo a este archivo, con como "Destino":
       powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\ruta\al\repo\actualizar_remoto_loop.ps1"
     (reemplazar la ruta por donde este clonado el repo en esa maquina).
  3. Esa ventana de PowerShell queda minimizada/oculta corriendo en bucle
     mientras la sesion siga abierta. Si la PC se reinicia o se cierra
     sesion, hay que volver a iniciar sesion para que arranque de nuevo
     (por eso esta pensado para una maquina que se deja logueada).
#>

param(
    [int]$IntervaloHoras = 3
)

while ($true) {
    & (Join-Path $PSScriptRoot "actualizar_remoto.ps1")
    Start-Sleep -Seconds ($IntervaloHoras * 3600)
}
