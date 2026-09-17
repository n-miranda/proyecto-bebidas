"""Serializa el resultado del consolidador a salida\\snapshot.json (CLAUDE.md
seccion 7.1: la web lee este archivo, no procesa Excel en cada request)."""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

from src.config import Config
from src.consolidador import ResultadoConsolidacion, consolidar

logger = logging.getLogger(__name__)


def _ruta_snapshot(config: Config) -> Path:
    return config.rutas.salida / "snapshot.json"


def generar_snapshot(config: Config, fecha_referencia: date | None = None) -> Path:
    resultado: ResultadoConsolidacion = consolidar(config, fecha_referencia)

    datos = {
        "meta": {
            **resultado.meta,
            "avisos": resultado.avisos,
        },
        "articulos": resultado.df.to_dict(orient="records"),
        "inconsistencias": resultado.inconsistencias,
    }

    config.rutas.salida.mkdir(parents=True, exist_ok=True)
    ruta = _ruta_snapshot(config)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    logger.info("Snapshot generado: %s (%d articulos)", ruta, len(resultado.df))
    return ruta


def cargar_snapshot(config: Config) -> dict:
    ruta = _ruta_snapshot(config)
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe {ruta} todavia. Hay que generar el snapshot primero "
            "(arrancar la app corre la actualizacion inicial automaticamente)."
        )
    return json.loads(ruta.read_text(encoding="utf-8"))
