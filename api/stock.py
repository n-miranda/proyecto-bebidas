"""Funcion serverless de Vercel: sirve los articulos de data/snapshot.json
tal cual los devuelve GET /api/stock en la app local (src/web/app.py) -- el
frontend (public/static/app.js) es el mismo codigo en los dos lados, solo
cambia de donde sale el dato: la app local recalcula desde los Excel en
cada arranque; esta funcion sirve una foto fija publicada a mano (ver
README para el paso de "republicar")."""
import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path

RUTA_SNAPSHOT = Path(__file__).resolve().parent.parent / "data" / "snapshot.json"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            snapshot = json.loads(RUTA_SNAPSHOT.read_text(encoding="utf-8"))
            cuerpo = json.dumps(snapshot["articulos"]).encode("utf-8")
            self.send_response(200)
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
            cuerpo = json.dumps({"error": f"No se pudo leer el snapshot publicado: {exc}"}).encode("utf-8")
            self.send_response(500)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=0, must-revalidate")
        self.end_headers()
        self.wfile.write(cuerpo)
