"""Punto de entrada: procesa las fuentes (genera salida\\snapshot.json) y
levanta la web Flask (CLAUDE.md seccion 3 y 7.1)."""
from __future__ import annotations

import logging
import sys
import webbrowser
from datetime import date
from pathlib import Path
from threading import Timer

from src.config import ConfigError, cargar_config
from src.snapshot import generar_snapshot
from src.web.app import crear_app

PUERTO = 5000


def _configurar_logging(carpeta_logs: Path) -> None:
    carpeta_logs.mkdir(parents=True, exist_ok=True)
    archivo_log = carpeta_logs / f"unificador_{date.today():%Y%m%d}.log"
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
    logger = logging.getLogger("main")

    try:
        generar_snapshot(config)
    except Exception as exc:  # noqa: BLE001 - error esperable de datos, se reporta en castellano
        logger.exception("Fallo la actualizacion inicial")
        print(f"No se pudo actualizar: {exc}")
        return 1

    app = crear_app()
    url = f"http://127.0.0.1:{PUERTO}/"
    print(f"Unificador de Stock disponible en {url}")
    Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=PUERTO, debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
