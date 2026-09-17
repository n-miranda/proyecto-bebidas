"""Rutas Flask + API JSON (CLAUDE.md seccion 7.1). La web lee
salida\\snapshot.json, no procesa Excel en cada request; el snapshot se
regenera al arrancar y bajo demanda via POST /api/actualizar."""
from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, jsonify, render_template

from src.config import cargar_config
from src.snapshot import cargar_snapshot, generar_snapshot

logger = logging.getLogger(__name__)


def crear_app() -> Flask:
    app = Flask(__name__)
    config = cargar_config()

    # Evita que el navegador sirva un app.js/estilos.css viejos de la cache
    # despues de un cambio: el query string cambia solo cuando cambia el
    # archivo, asi que el navegador siempre revalida.
    carpeta_static = Path(app.static_folder)

    @app.context_processor
    def _version_estaticos():
        def v(nombre_archivo: str) -> int:
            try:
                return int((carpeta_static / nombre_archivo).stat().st_mtime)
            except OSError:
                return 0
        return {"v": v}
    umbrales = {
        "rojo_hasta": config.semaforo_dias_stock.rojo_hasta,
        "amarillo_hasta": config.semaforo_dias_stock.amarillo_hasta,
        "verde_hasta": config.semaforo_dias_stock.verde_hasta,
    }

    def _respuesta_meta(datos: dict):
        return jsonify({
            "meta": datos["meta"],
            "inconsistencias": datos["inconsistencias"],
            "umbrales_semaforo": umbrales,
        })

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/stock-general")
    def stock_general():
        return render_template("stock_general.html")

    @app.get("/api/stock")
    def api_stock():
        try:
            datos = cargar_snapshot(config)
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404
        return jsonify(datos["articulos"])

    @app.get("/api/meta")
    def api_meta():
        try:
            datos = cargar_snapshot(config)
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404
        return _respuesta_meta(datos)

    @app.post("/api/actualizar")
    def api_actualizar():
        try:
            generar_snapshot(config)
            datos = cargar_snapshot(config)
        except Exception as exc:  # noqa: BLE001 - error esperable de datos, se reporta en castellano
            logger.exception("Fallo la actualizacion")
            return jsonify({"error": str(exc)}), 500
        return _respuesta_meta(datos)

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    crear_app().run(debug=True, port=5000)
