"""Punto de entrada de la web paralela (src/web_v2) para probar cambios
estructurales de interfaz sin tocar la version en produccion (src/web).

A diferencia de src/main.py, esta NO regenera salida\\snapshot.json al
arrancar -- reutiliza el que ya haya (compartido con la web original, mismo
calculo, mismo config.json). Si todavia no existe ninguno, corre primero
`python -m src.main` una vez, o usa el boton "Actualizar datos" en esta
misma web."""
from __future__ import annotations

import logging
import sys
import webbrowser
from datetime import date
from pathlib import Path
from threading import Timer

from src.config import ConfigError, cargar_config
from src.web_v2.app import crear_app

PUERTO = 5001


def _configurar_logging(carpeta_logs: Path) -> None:
    carpeta_logs.mkdir(parents=True, exist_ok=True)
    archivo_log = carpeta_logs / f"unificador_v2_{date.today():%Y%m%d}.log"
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

    app = crear_app()
    url = f"http://127.0.0.1:{PUERTO}/"
    print(f"Unificador de Stock (version paralela) disponible en {url}")
    Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=PUERTO, debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
