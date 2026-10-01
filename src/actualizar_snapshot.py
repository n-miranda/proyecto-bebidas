"""Punto de entrada headless: genera salida\\snapshot.json y lo copia a
data\\snapshot.json, sin levantar Flask ni abrir el navegador (a diferencia
de src\\main.py). Pensado para correr desatendido -- Programador de tareas
de Windows / cron -- en una maquina con acceso de red a las bases de origen
(ver README, seccion "Automatizar la actualizacion desde un servidor
remoto"): ese es el primer paso de actualizar_remoto.ps1, que despues sube
data\\snapshot.json a git para que Vercel redespliegue solo."""
from __future__ import annotations

import logging
import shutil
import sys
from datetime import date
from pathlib import Path

from src.config import ConfigError, RAIZ_PROYECTO, cargar_config
from src.snapshot import generar_snapshot

RUTA_SNAPSHOT_PUBLICADO = RAIZ_PROYECTO / "data" / "snapshot.json"


def _configurar_logging(carpeta_logs: Path) -> None:
    carpeta_logs.mkdir(parents=True, exist_ok=True)
    archivo_log = carpeta_logs / f"actualizar_snapshot_{date.today():%Y%m%d}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(archivo_log, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
    )


def main() -> int:
    try:
        config = cargar_config()
    except ConfigError as exc:
        print(f"Error de configuracion: {exc}")
        return 1

    _configurar_logging(config.rutas.logs)
    logger = logging.getLogger("actualizar_snapshot")

    try:
        ruta_snapshot = generar_snapshot(config)
    except Exception as exc:  # noqa: BLE001 - error esperable de datos, se reporta en castellano
        logger.exception("Fallo la generacion del snapshot")
        print(f"No se pudo generar el snapshot: {exc}")
        return 1

    RUTA_SNAPSHOT_PUBLICADO.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ruta_snapshot, RUTA_SNAPSHOT_PUBLICADO)
    logger.info("Snapshot copiado a %s", RUTA_SNAPSHOT_PUBLICADO)
    print(f"Snapshot actualizado: {RUTA_SNAPSHOT_PUBLICADO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
